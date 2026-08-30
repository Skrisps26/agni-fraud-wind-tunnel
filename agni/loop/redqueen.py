"""Red Queen engine - the closed loop that makes AGNI a wind tunnel."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from agni.agents.critic import critic_brief
from agni.agents.scout import scout_propose
from agni.config import Config, load
from agni.defense.baseline import bank_checklist, evaluate_baseline, rules_predict, vector_det_rates
from agni.defense.features import FEATURES, build_dataset
from agni.defense.model import FusionDetector
from agni.eval.harness import protocol_block
from agni.foundry.base import AttackContext, build_playbook
from agni.foundry.judge import joint_mmd, judge_all
from agni.genome.atlas import coverage_matrix
from agni.genome.schema import AttackGenome, clone_with_params, load_genomes, propose_variant
from agni.twin.calibrate import load_anchor_sample, load_calibration
from agni.twin.population import Population
from agni.twin.rails import Simulation


@dataclass
class RedQueenResult:
    history: list[dict] = field(default_factory=list)
    genomes_final: list[dict] = field(default_factory=list)
    agent_log: list[dict] = field(default_factory=list)
    vector_det_rates: dict[str, float] = field(default_factory=dict)
    mule_graph: dict = field(default_factory=dict)
    tte_generations: int = 0
    loop_gain_auc: float = 0.0
    fidelity_overall: float = 0.0
    joint_mmd: float = 0.0
    atlas: dict = field(default_factory=dict)
    protocol: dict = field(default_factory=dict)
    shadow: dict = field(default_factory=dict)
    league: list[dict] = field(default_factory=list)
    total_legit_txns: int = 0
    total_attack_txns: int = 0

    def to_json(self) -> dict:
        return asdict(self)


def _feature_blind_spots(X: pd.DataFrame, meta: pd.DataFrame, p_all: np.ndarray,
                         thr: float, genome_of: dict[str, str],
                         rate_by_aid: dict[str, float]) -> dict[str, list[str]]:
    hints: dict[str, list[str]] = {}
    if not len(X) or not rate_by_aid:
        return hints
    flagged = p_all >= thr
    for aid, det_rate in rate_by_aid.items():
        if det_rate >= 0.7:
            continue
        gid = genome_of.get(aid)
        if not gid:
            continue
        mask = (meta["attack_id"].to_numpy() == aid)
        missed = mask & ~flagged
        caught = mask & flagged
        if missed.sum() < 2 or caught.sum() < 2:
            continue
        low_feats = []
        for feat in FEATURES:
            m_val = float(X.loc[missed, feat].mean())
            c_val = float(X.loc[caught, feat].mean())
            if c_val > 0.5 and m_val < c_val * 0.6:
                low_feats.append(feat)
        if low_feats:
            hints.setdefault(gid, []).extend(low_feats[:3])
    return {k: list(dict.fromkeys(v))[:3] for k, v in hints.items()}


def _gid_from_aid(aid: str, genome_of: dict[str, str]) -> str:
    if aid in genome_of:
        return genome_of[aid]
    return aid.rsplit("-g", 1)[0] if "-g" in aid else aid


def _mule_graph(meta: pd.DataFrame, top_n: int = 18) -> dict:
    """Compact src-dst graph of fraud txns for the UI mule strip."""
    if meta is None or not len(meta):
        return {"nodes": [], "edges": []}
    fraud = meta[meta["is_fraud"] == 1]
    if not len(fraud):
        return {"nodes": [], "edges": []}
    fan = fraud.groupby("dst").size().sort_values(ascending=False)
    sink = str(fan.index[0]) if len(fan) else None
    sub = fraud[fraud["dst"] == sink].head(top_n) if sink else fraud.head(top_n)
    nodes, seen = [], set()
    edges = []
    for r in sub.itertuples():
        for n in (str(r.src), str(r.dst)):
            if n not in seen:
                seen.add(n)
                nodes.append({"id": n, "sink": n == sink})
        edges.append({"src": str(r.src), "dst": str(r.dst),
                      "amount": float(r.amount)})
    return {"nodes": nodes, "edges": edges, "sink": sink}


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
    agent_log: list[dict] = []
    history: list[dict] = []
    frozen: FusionDetector | None = None
    last_thr = 0.5
    streak = 0
    last_det_rate: dict[str, float] = {}
    blind_spots: dict[str, list[str]] = {}
    last_vector_rates: dict[str, float] = {}
    p_all = np.array([])
    meta = pd.DataFrame()
    X = pd.DataFrame()
    thr = 0.5
    arts = pd.DataFrame()
    defender = FusionDetector(cfg.seed, cfg.text_blend_weight)
    last_genome_of: dict[str, str] = {}

    for g in range(G):
        t0 = time.time()
        gen_rng = np.random.default_rng(rng.integers(2 ** 62))
        sim = Simulation(pop, days=cfg.days, daily_lambda=cfg.daily_txn_lambda,
                         benign_msg_cap=cfg.benign_msg_cap)
        sim.background_traffic(gen_rng)

        genome_of: dict[str, str] = {}
        held = set(cfg.held_out_playbooks)
        for genome in genomes:
            if g == 0 and genome.playbook in held:
                continue
            try:
                pb = build_playbook(genome)
            except KeyError:
                continue
            fb = {"det_rate": last_det_rate.get(genome.id, 0.0),
                  "blind_spots": blind_spots.get(genome.id, [])}
            for r in range(cfg.runs_per_genome):
                aid = f"{genome.id}-g{g}r{r}"
                genome_of[aid] = genome.id
                ctx = AttackContext(
                    sim, np.random.default_rng(rng.integers(2 ** 62)),
                    aid, dict(genome.params), feedback=dict(fb),
                    genome_id=genome.id, playbook=genome.playbook)
                try:
                    pb.execute(ctx)
                except Exception as exc:
                    if verbose:
                        print(f"  [warn] {genome.id} failed: {exc!r}")

        last_genome_of = dict(genome_of)

        reports = judge_all(sim, genome_of, anchor=anchor)
        fid_mean = float(np.mean([r.overall for r in reports])) if reports else 0.0
        j_mmd = joint_mmd(sim.ledger.to_df())

        X, meta = build_dataset(sim)
        y = meta["is_fraud"].to_numpy()
        cut = int(len(meta) * 0.8)
        boundary = meta["ts"].iloc[cut]
        arts = sim.ledger.artifacts_df()
        if len(arts):
            arts["ts"] = pd.to_datetime(arts["ts"])
        arts_tr = arts[arts.ts < boundary].drop(columns=["ts"]) if len(arts) else None
        arts_te = arts[arts.ts >= boundary] if len(arts) else arts

        evasion = g > 0 and g <= cfg.evasion_gens and frozen is not None
        te_scores = defender.account_text_scores(arts_te if len(arts) else None)

        if evasion:
            p_test = frozen.predict_proba(X.iloc[cut:], te_scores)
            thr = last_thr
            m_new = FusionDetector.evaluate(p_test, y[cut:], thr, cfg.fpr_budget)
            defender = frozen
            agent_log.append({"agent": "critic", "gen": g,
                              "message": f"[Evasion pressure gen {g}] Frozen defender held — "
                                         "attacks mutating without retrain."})
        else:
            defender = FusionDetector(cfg.seed, cfg.text_blend_weight)
            defender.fit(X.iloc[:cut], y[:cut], arts_tr)
            te_scores = defender.account_text_scores(arts_te if len(arts) else None)
            p_test = defender.predict_proba(X.iloc[cut:], te_scores)
            y_test = y[cut:]
            thr = FusionDetector.choose_threshold(p_test, y_test, cfg.fpr_budget)
            m_new = FusionDetector.evaluate(p_test, y_test, thr, cfg.fpr_budget)
            last_thr = thr

        all_scores = defender.account_text_scores(arts if len(arts) else None)
        p_all = defender.predict_proba(X, all_scores)

        frozen_eval = None
        if frozen is not None and not evasion:
            fp = frozen.predict_proba(X.iloc[cut:], te_scores)
            frozen_eval = round(float(roc_auc_score(y[cut:], fp)), 4)
            streak = streak + 1 if frozen_eval >= cfg.tte_threshold else 0
            result.tte_generations = max(result.tte_generations, streak)
        elif evasion and frozen is not None:
            fp = frozen.predict_proba(X.iloc[cut:], te_scores)
            frozen_eval = round(float(roc_auc_score(y[cut:], fp)), 4)
            streak = streak + 1 if frozen_eval >= cfg.tte_threshold else 0
            result.tte_generations = max(result.tte_generations, streak)

        if not evasion:
            frozen = defender

        baseline = evaluate_baseline(sim)

        rate_by_aid: dict[str, float] = {}
        mask_atk = meta["attack_id"].to_numpy() != ""
        if mask_atk.any():
            sub = pd.DataFrame({"aid": meta["attack_id"][mask_atk],
                                "hit": (p_all[mask_atk] >= thr)})
            rate_by_aid = sub.groupby("aid")["hit"].mean().to_dict()
        last_vector_rates = vector_det_rates(meta, p_all, thr, genome_of)
        proto = protocol_block(
            X, y, meta, p_all, thr, genome_of, cut, cfg.fpr_budget,
            cfg.target_fraud_rate, cfg.held_out_playbooks, genomes, cfg.seed)
        proto["lab_auc"] = m_new.get("roc_auc")
        proto["joint_mmd"] = j_mmd
        proto["checklist_recall"] = baseline.get("checklist_recall")

        entry = {
            "generation": g, "legit_txns": int((y == 0).sum()),
            "attack_txns": int((y == 1).sum()),
            "fraud_rate_pct": round(100 * float(y.mean()), 3),
            **m_new,
            "frozen_auc": frozen_eval,
            "fidelity_mean": round(fid_mean, 4),
            "n_attacks_run": len(genome_of),
            "evasion_pressure": evasion,
            "baseline_recall": baseline["baseline_recall"],
            "baseline_precision": baseline["baseline_precision"],
            "checklist_recall": baseline.get("checklist_recall"),
            "vector_det_rates": last_vector_rates,
            "protocol": proto,
            "secs": round(time.time() - t0, 1),
        }
        history.append(entry)
        if verbose:
            fe = "-" if frozen_eval is None else f"{frozen_eval:.3f}"
            ev = " EVASION" if evasion else ""
            print(f"gen {g}: auc={m_new['roc_auc']:.3f} rec={m_new['recall']:.3f} "
                  f"fpr={m_new['fpr']:.4%} fidelity={fid_mean:.2f} "
                  f"frozenAUC={fe} rules_rec={baseline['baseline_recall']:.2%} "
                  f"holdoutAUC={proto.get('family_holdout_auc')} "
                  f"rec@base={proto.get('recall_at_base_rate')}{ev} "
                  f"({entry['secs']}s)")

        last_det_rate = {}
        for aid, hit in rate_by_aid.items():
            gid = _gid_from_aid(aid, genome_of)
            last_det_rate.setdefault(gid, []).append(float(hit))
        last_det_rate = {k: float(np.mean(v)) for k, v in last_det_rate.items()}
        blind_spots = _feature_blind_spots(X, meta, p_all, thr, genome_of, rate_by_aid)

        weakest = min(last_det_rate, key=last_det_rate.get, default=None) if last_det_rate else None
        mutate_thresh = 0.92 if evasion else 0.85
        already_child = {g.family() for g in genomes if g.parent_ids}

        nxt = []
        probe_ctx = AttackContext(sim, gen_rng, "probe", {}, feedback={"det_rate": 0.0})
        for genome in genomes:
            dr = last_det_rate.get(genome.id)
            if (dr is not None and dr < mutate_thresh and len(nxt) < cfg.max_genomes - 1
                    and genome.family() not in already_child):
                try:
                    pb = build_playbook(genome)
                    probe_ctx.feedback = {
                        "det_rate": dr,
                        "blind_spots": blind_spots.get(genome.id, []),
                    }
                    ov = pb.mutate(probe_ctx)
                    mutated = clone_with_params(genome, ov, g + 1)
                    mutated.id = f"{genome.id}-m{g + 1}"
                    mutated.name = f"{genome.name} (mutated)"
                    nxt.append(mutated)
                    msg = critic_brief(genome, dr, blind_spots.get(genome.id, []),
                                       frozen_eval, g)
                    agent_log.append({"agent": "critic", "gen": g, "message": msg})
                    continue
                except Exception:
                    pass
            nxt.append(genome)

        if (g + 1) % 2 == 0 and len(nxt) < cfg.max_genomes:
            base = next((x for x in nxt if x.id == weakest), None) if weakest else None
            if base is not None:
                nxt.append(propose_variant(base, None, g + 1))

        if (g + 1) % 2 == 0 and len(nxt) < cfg.max_genomes:
            scout_genome, scout_msg = scout_propose(
                g + 1, blind_spots, weakest, genomes)
            agent_log.append({"agent": "scout", "gen": g, "message": scout_msg})
            if scout_genome is not None:
                nxt.append(scout_genome)

        genomes = nxt[: cfg.max_genomes]

    result.history = history
    result.genomes_final = [json.loads(g.model_dump_json()) for g in genomes]
    result.agent_log = agent_log
    result.vector_det_rates = last_vector_rates
    result.mule_graph = _mule_graph(meta)
    result.loop_gain_auc = round(history[-1]["roc_auc"] - history[0]["roc_auc"], 4)
    result.fidelity_overall = round(float(np.mean(
        [h["fidelity_mean"] for h in history])), 4)
    result.joint_mmd = round(float(np.mean(
        [h.get("protocol", {}).get("joint_mmd") or 0 for h in history])), 4)
    result.atlas = coverage_matrix(genomes)
    result.protocol = history[-1].get("protocol") or {}
    result.shadow = {
        "frozen_auc_curve": [h.get("frozen_auc") for h in history],
        "tte_generations": result.tte_generations,
        "fpr_budget": cfg.fpr_budget,
        "note": "Shadow: frozen Sentinel vs Critic mutations. Not a live DI deploy.",
    }
    result.league = [
        {
            "generation": h["generation"],
            "coverage": result.atlas.get("coverage"),
            "fidelity_mmd": (h.get("protocol") or {}).get("joint_mmd"),
            "tte": result.tte_generations,
            "recall_at_0_5_fpr": h.get("recall"),
            "recall_at_base_rate": (h.get("protocol") or {}).get("recall_at_base_rate"),
            "family_holdout_auc": (h.get("protocol") or {}).get("family_holdout_auc"),
        }
        for h in history
    ]
    result.total_legit_txns = sum(h["legit_txns"] for h in history)
    result.total_attack_txns = sum(h["attack_txns"] for h in history)
    return result, {"p_all": p_all, "meta": meta, "X": X, "thr": thr,
                    "arts": arts, "defender": defender,
                    "agent_log": agent_log, "vector_det_rates": last_vector_rates,
                    "mule_graph": result.mule_graph, "genome_of": last_genome_of,
                    "genomes": genomes}


def _alerts(payload_extra: dict, top_k: int = 12) -> list[dict]:
    p_all = payload_extra["p_all"]
    meta = payload_extra["meta"]
    thr = payload_extra["thr"]
    X = payload_extra.get("X")
    defender = payload_extra.get("defender")
    idx = np.argsort(-p_all)[:top_k * 4]
    seen, out = set(), []
    for i in idx:
        row = meta.iloc[i]
        if row.txn_id in seen:
            continue
        seen.add(row.txn_id)
        expl = []
        ticket = {}
        if defender is not None and X is not None:
            expl = defender.explain(X, i, top_k=3)
            ticket = defender.case_ticket(X, i)
        out.append({
            "txn_id": str(row.txn_id), "score": round(float(p_all[i]), 4),
            "flag": bool(p_all[i] >= thr), "is_fraud": int(row.is_fraud),
            "src": str(row.src), "dst": str(row.dst),
            "amount": float(row.amount), "ts": str(row.ts),
            "attack_id": str(row.attack_id),
            "explanations": expl,
            "ticket": ticket,
        })
        if len(out) >= top_k:
            break
    return out


def _artifact_feed(payload_extra: dict, top_k: int = 15) -> list[dict]:
    arts = payload_extra.get("arts")
    if arts is None or not len(arts):
        return []
    fraud = arts[arts.label == 1] if "label" in arts.columns else arts
    if not len(fraud):
        return []
    recent = fraud.sort_values("ts", ascending=False)
    per_kind_cap = 4
    counts: dict[str, int] = {}
    picked = []
    for r in recent.itertuples():
        k = str(r.kind)
        if counts.get(k, 0) >= per_kind_cap:
            continue
        counts[k] = counts.get(k, 0) + 1
        forge = getattr(r, "forge_source", "template")
        picked.append({
            "ts": str(r.ts), "src": str(r.src), "kind": k,
            "text": str(r.text)[:320], "attack_id": str(r.attack_id),
            "forge_source": forge,
        })
        if len(picked) >= top_k:
            break
    picked.reverse()
    return picked


_ARTIFACT_LABELS = {
    "call_transcript": "Voice call (synthetic)",
    "chat": "Chat / support bot",
    "email": "Email lure",
    "sms": "Phishing SMS",
    "listing": "Agentic checkout listing",
    "note": "Card harvest",
}


def _stage_for_kind(kind: str) -> int:
    if kind in ("call_transcript", "chat", "email"):
        return 1
    if kind == "sms":
        return 2
    if kind == "listing":
        return 3
    if kind == "note":
        return 4
    return 4


def _build_demo_chains(extra: dict, genome_of: dict) -> dict[str, list]:
    """Per-genome kill chains with Sentinel vs rules verdicts on each transfer."""
    meta = extra.get("meta")
    X = extra.get("X")
    p_all = extra.get("p_all")
    thr = float(extra.get("thr") or 0.5)
    arts = extra.get("arts")
    if meta is None or not len(meta) or p_all is None or not len(p_all):
        return {}

    rules = rules_predict(X) if X is not None and len(X) else np.zeros(len(meta))

    # Best attack run per genome base (most artifacts + transfers).
    candidates: dict[str, list[str]] = {}
    for aid, gid in genome_of.items():
        base = _gid_from_aid(aid, {aid: gid})
        candidates.setdefault(base, []).append(aid)

    chains: dict[str, list] = {}
    for base, aids in candidates.items():
        best_aid, best_steps = None, []
        for aid in aids:
            steps = _chain_for_attack(aid, meta, p_all, thr, rules, arts)
            if len(steps) > len(best_steps):
                best_aid, best_steps = aid, steps
        if best_steps:
            chains[base] = best_steps
    return chains


def _chain_for_attack(aid: str, meta: pd.DataFrame, p_all: np.ndarray, thr: float,
                      rules: np.ndarray, arts: pd.DataFrame | None) -> list[dict]:
    steps: list[dict] = []
    if arts is not None and len(arts) and "attack_id" in arts.columns:
        sub = arts[arts["attack_id"] == aid].sort_values("ts")
        for r in sub.itertuples():
            kind = str(r.kind)
            steps.append({
                "type": "artifact",
                "ts": str(r.ts),
                "stage": _stage_for_kind(kind),
                "title": _ARTIFACT_LABELS.get(kind, kind),
                "body": str(r.text)[:420],
                "llm": str(getattr(r, "forge_source", "")) == "llm",
            })

    for i in range(len(meta)):
        row = meta.iloc[i]
        if str(row["attack_id"]) != aid or int(row["is_fraud"]) != 1:
            continue
        score = float(p_all[i])
        steps.append({
            "type": "transfer",
            "ts": str(row["ts"]),
            "stage": 5,
            "title": f"UPI ₹{float(row['amount']):,.0f}",
            "body": f"{row['src']} → {row['dst']}",
            "amount": float(row["amount"]),
            "sentinel_score": round(score, 4),
            "sentinel_caught": bool(score >= thr),
            "rules_caught": bool(rules[i]),
        })

    steps.sort(key=lambda s: s["ts"])
    return steps


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
    print(f"agent log entries: {len(result.agent_log)}")

    out_dir = Path(__file__).resolve().parents[2] / "runs"
    out_dir.mkdir(exist_ok=True)
    payload = result.to_json()
    payload["alerts"] = _alerts(extra)
    payload["artifacts"] = _artifact_feed(extra)
    payload["mule_graph"] = extra.get("mule_graph", {})
    payload["demo_chains"] = _build_demo_chains(extra, extra.get("genome_of") or {})
    payload["atlas"] = result.atlas
    payload["protocol"] = result.protocol
    payload["shadow"] = result.shadow
    payload["league"] = result.league
    payload["joint_mmd"] = result.joint_mmd
    (out_dir / "latest.json").write_text(json.dumps(payload, indent=1))
    print(f"wrote {out_dir / 'latest.json'}")


if __name__ == "__main__":
    main()
