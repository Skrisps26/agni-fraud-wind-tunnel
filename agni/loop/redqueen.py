"""Red Queen engine - the closed loop that makes AGNI a wind tunnel.

Per generation:
  1. twin regenerates legitimate traffic,
  2. Foundry executes every genome's playbook (mutated lineage carried over),
  3. Fidelity Judge scores realism of each attack (vs REAL anchor when present),
  4. Sentinel retrains on the labeled stream; metrics reported on a time holdout,
  5. the PREVIOUS generation's defender is evaluated frozen on the new attacks
     (this yields Time-to-Evade),
  6. under-detected genomes are mutated toward evasion; the Critic occasionally
     proposes parameter-regime siblings (diversity growth).

Everything runs offline and deterministically under a single seed.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from agni.config import Config, load
from agni.defense.features import build_dataset
from agni.defense.model import FusionDetector
from agni.foundry.base import AttackContext, build_playbook
from agni.foundry.judge import judge_all
from agni.genome.schema import clone_with_params, load_genomes, propose_variant
from agni.twin.calibrate import load_anchor_sample, load_calibration
from agni.twin.population import Population
from agni.twin.rails import Simulation


@dataclass
class RedQueenResult:
    history: list[dict] = field(default_factory=list)
    genomes_final: list[dict] = field(default_factory=list)
    tte_generations: int = 0
    loop_gain_auc: float = 0.0
    fidelity_overall: float = 0.0
    total_legit_txns: int = 0
    total_attack_txns: int = 0

    def to_json(self) -> dict:
        return asdict(self)


def run_loop(cfg: Config | None = None, generations: int | None = None,
             verbose: bool = True) -> tuple[RedQueenResult, dict]:
    cfg = cfg or load()
    G = generations if generations is not None else cfg.generations
    rng = np.random.default_rng(cfg.seed)

    calibration = load_calibration()
    anchor = load_anchor_sample()
    pop = Population.generate(cfg.consumers, cfg.merchants, rng,
                              calibration=calibration)
    if verbose and (calibration or anchor):
        src = (anchor or {}).get("source") or (calibration or {}).get("source")
        print(f"real-data anchoring active: {src}")
    genomes = load_genomes()
    result = RedQueenResult()
    history: list[dict] = []
    frozen: FusionDetector | None = None
    streak = 0
    last_det_rate: dict[str, float] = {}

    for g in range(G):
        t0 = time.time()
        gen_rng = np.random.default_rng(rng.integers(2 ** 62))
        sim = Simulation(pop, days=cfg.days)
        sim.background_traffic(gen_rng)

        # ---- 2. attacks ---------------------------------------------------
        genome_of: dict[str, str] = {}
        for genome in genomes:
            try:
                pb = build_playbook(genome)
            except KeyError:
                continue
            fb = {"det_rate": last_det_rate.get(genome.id, 0.0)}
            for r in range(cfg.runs_per_genome):
                aid = f"{genome.id}-g{g}r{r}"
                genome_of[aid] = genome.id
                ctx = AttackContext(sim, np.random.default_rng(rng.integers(2 ** 62)),
                                    aid, dict(genome.params), feedback=dict(fb))
                try:
                    pb.execute(ctx)
                except Exception as exc:  # a broken vector must not kill the loop
                    if verbose:
                        print(f"  [warn] {genome.id} failed: {exc!r}")

        # ---- 3. fidelity --------------------------------------------------
        reports = judge_all(sim, genome_of, anchor=anchor)
        fid_by_gid: dict[str, list[float]] = {}
        for rep in reports:
            fid_by_gid.setdefault(rep.genome_id, []).append(rep.overall)
        fid_mean = float(np.mean([r.overall for r in reports])) if reports else 0.0

        # ---- 4. defend ----------------------------------------------------
        X, meta = build_dataset(sim)
        y = meta["is_fraud"].to_numpy()
        cut = int(len(meta) * 0.8)
        boundary = meta["ts"].iloc[cut]
        arts = sim.ledger.artifacts_df()
        if len(arts):
            arts["ts"] = pd.to_datetime(arts["ts"])
        arts_tr = arts[arts.ts < boundary].drop(columns=["ts"]) if len(arts) else None
        arts_te = arts[arts.ts >= boundary] if len(arts) else arts

        defender = FusionDetector(cfg.seed, cfg.text_blend_weight)
        defender.fit(X.iloc[:cut], y[:cut], arts_tr)
        te_scores = defender.account_text_scores(arts_te if len(arts) else None)
        p_test = defender.predict_proba(X.iloc[cut:], te_scores)
        y_test = y[cut:]
        thr = FusionDetector.choose_threshold(p_test, y_test, cfg.fpr_budget)
        m_new = FusionDetector.evaluate(p_test, y_test, thr, cfg.fpr_budget)

        # full-stream scores for per-attack feedback + alerts
        all_scores = defender.account_text_scores(arts if len(arts) else None)
        p_all = defender.predict_proba(X, all_scores)

        # ---- 5. frozen-drift / TtE ----------------------------------------
        frozen_eval = None
        if frozen is not None:
            fp = frozen.predict_proba(X.iloc[cut:], te_scores)
            frozen_eval = round(float(roc_auc_score(y_test, fp)), 4)
            streak = streak + 1 if frozen_eval >= cfg.tte_threshold else 0
            result.tte_generations = max(result.tte_generations, streak)
        frozen = defender  # freeze newest for next generation

        # per-attack detection rate (full stream view, thresholded)
        rate_by_aid: dict[str, float] = {}
        mask_atk = meta["attack_id"].to_numpy() != ""
        if mask_atk.any():
            sub = pd.DataFrame({"aid": meta["attack_id"][mask_atk],
                                "hit": (p_all[mask_atk] >= thr)})
            rate_by_aid = sub.groupby("aid")["hit"].mean().to_dict()

        entry = {
            "generation": g, "legit_txns": int((y == 0).sum()),
            "attack_txns": int((y == 1).sum()),
            "fraud_rate_pct": round(100 * float(y.mean()), 3),
            **m_new,
            "frozen_auc": frozen_eval,
            "fidelity_mean": round(fid_mean, 4),
            "n_attacks_run": len(genome_of),
            "secs": round(time.time() - t0, 1),
        }
        history.append(entry)
        if verbose:
            fe = "-" if frozen_eval is None else f"{frozen_eval:.3f}"
            print(f"gen {g}: auc={m_new['roc_auc']:.3f} rec={m_new['recall']:.3f} "
                  f"fpr={m_new['fpr']:.4%} fidelity={fid_mean:.2f} "
                  f"frozenAUC={fe} attacks={len(genome_of)} ({entry['secs']}s)")

        # ---- 6. evolve -----------------------------------------------------
        last_det_rate = {}
        for aid, hit in rate_by_aid.items():
            gid = genome_of.get(aid)
            if gid:
                last_det_rate.setdefault(gid, []).append(float(hit))
        last_det_rate = {k: float(np.mean(v)) for k, v in last_det_rate.items()}

        nxt = []
        probe_ctx = AttackContext(sim, gen_rng, "probe", {}, {})
        for genome in genomes:
            dr = last_det_rate.get(genome.id)
            if dr is not None and dr < 0.7 and len(nxt) < cfg.max_genomes - 1:
                try:
                    ov = build_playbook(genome).mutate(probe_ctx)
                    nxt.append(clone_with_params(genome, ov, g + 1))
                    continue
                except Exception:
                    pass
            nxt.append(genome)
        if (g + 1) % 3 == 0 and len(nxt) < cfg.max_genomes:
            weakest = min(last_det_rate, key=lambda k: last_det_rate[k],
                          default=None)
            base = next((x for x in nxt if x.id == weakest), None)
            if base is not None:
                nxt.append(propose_variant(base, {}, g + 1))
        genomes = nxt[: cfg.max_genomes]

    # ---------------------------------------------------------------- wrap up
    result.history = history
    result.genomes_final = [json.loads(g.model_dump_json()) for g in genomes]
    result.loop_gain_auc = round(history[-1]["roc_auc"] - history[0]["roc_auc"], 4)
    result.fidelity_overall = round(float(np.mean(
        [h["fidelity_mean"] for h in history])), 4)
    result.total_legit_txns = sum(h["legit_txns"] for h in history)
    result.total_attack_txns = sum(h["attack_txns"] for h in history)
    return result, {"p_all": p_all, "meta": meta, "X": X, "thr": thr}


def _alerts(payload_extra: dict, top_k: int = 12) -> list[dict]:
    """Top scored suspicious txns from the last generation (demo feed)."""
    p_all = payload_extra["p_all"]
    meta = payload_extra["meta"]
    thr = payload_extra["thr"]
    idx = np.argsort(-p_all)[:top_k * 4]
    seen, out = set(), []
    for i in idx:
        row = meta.iloc[i]
        if row.txn_id in seen:
            continue
        seen.add(row.txn_id)
        out.append({
            "txn_id": str(row.txn_id), "score": round(float(p_all[i]), 4),
            "flag": bool(p_all[i] >= thr), "is_fraud": int(row.is_fraud),
            "src": str(row.src), "dst": str(row.dst),
            "amount": float(row.amount), "ts": str(row.ts),
            "attack_id": str(row.attack_id),
        })
        if len(out) >= top_k:
            break
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="AGNI Fraud Wind Tunnel")
    ap.add_argument("--generations", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--consumers", type=int, default=None)
    ap.add_argument("--days", type=int, default=None)
    args = ap.parse_args()

    cfg = load()
    if args.seed is not None:
        cfg.seed = args.seed
    if args.consumers is not None:
        cfg.consumers = args.consumers
    if args.days is not None:
        cfg.days = args.days

    print(f"AGNI wind tunnel: seed={cfg.seed} consumers={cfg.consumers} "
          f"days={cfg.days} generations={args.generations or cfg.generations}")
    result, extra = run_loop(cfg, generations=args.generations)

    print("\n=== Red Queen summary ===")
    print(f"time-to-evade (frozen gens survived): {result.tte_generations}")
    print(f"loop gain dAUC: {result.loop_gain_auc:+.3f}")
    print(f"attacks executed across run: {result.total_attack_txns:,}")
    print(f"mean fidelity vs reference: {result.fidelity_overall}")
    print(f"genome count final: {len(result.genomes_final)}")

    out_dir = Path(__file__).resolve().parents[2] / "runs"
    out_dir.mkdir(exist_ok=True)
    payload = result.to_json()
    payload["alerts"] = _alerts(extra)
    (out_dir / "latest.json").write_text(json.dumps(payload, indent=1))
    print(f"wrote {out_dir / 'latest.json'}")


if __name__ == "__main__":
    main()
