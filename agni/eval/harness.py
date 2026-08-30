"""Honest evaluation harness — family holdout, base-rate replay, ablation, TtE.

In-generator AUC is reported as `roc_auc` (lab) and must not be the headline.
Headlines: recall_at_base_rate, family_holdout_auc, frozen_auc / time-to-evade.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.metrics import roc_auc_score

from agni.defense.features import FEATURES
from agni.defense.model import FusionDetector

GRAPH_FEATS = [
    "dst_fan_in", "dst_max_src_share", "dst_fwd_rate_24h",
    "dst_unique_src_1h", "src_new_dst_24h", "new_dst_pair",
]
SEQ_FEATS = ["vel_10m", "vel_1h", "vel_24h", "vel_ratio_10m_24h", "interarrival_log"]
TABULAR_FEATS = [f for f in FEATURES if f not in GRAPH_FEATS]

# Playbook families withheld from gen-0 train (must match Config.held_out_playbooks).
DEFAULT_HOLD_FAMILIES = (
    "mule_graph_ring", "subscription_mandate_trap", "npci_chatbot_phish",
)


def downsample_to_base_rate(
    y: np.ndarray, p: np.ndarray, target_rate: float, rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Keep all legit; subsample fraud so P(fraud) ≈ target_rate (production prior)."""
    y = np.asarray(y)
    p = np.asarray(p)
    pos = np.where(y == 1)[0]
    neg = np.where(y == 0)[0]
    if not len(pos) or not len(neg) or target_rate <= 0:
        return y, p
    want = int(round(target_rate / max(1 - target_rate, 1e-9) * len(neg)))
    want = max(1, min(want, len(pos)))
    keep_pos = rng.choice(pos, size=want, replace=False)
    idx = np.concatenate([neg, keep_pos])
    rng.shuffle(idx)
    return y[idx], p[idx]


def metrics_at_base_rate(p: np.ndarray, y: np.ndarray, thr: float,
                         target_rate: float, fpr_budget: float,
                         seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    yb, pb = downsample_to_base_rate(y, p, target_rate, rng)
    out = FusionDetector.evaluate(pb, yb, thr, fpr_budget)
    out["fraud_rate"] = round(float(yb.mean()), 5)
    out["n"] = int(len(yb))
    return out


def family_holdout_auc(p: np.ndarray, y: np.ndarray, meta: pd.DataFrame,
                       genome_of: dict[str, str],
                       family_playbooks: tuple[str, ...],
                       genomes: list | None = None) -> dict:
    """AUC on txns whose genome playbook is in the holdout set vs the rest."""
    play_of: dict[str, str] = {}
    if genomes:
        play_of = {g.id: g.playbook for g in genomes}
        for g in genomes:
            play_of.setdefault(g.family(), g.playbook)

    fam = set(family_playbooks)
    aids = meta["attack_id"].astype(str).to_numpy()
    is_hold = np.zeros(len(meta), dtype=bool)
    for i, aid in enumerate(aids):
        if not aid:
            continue
        gid = genome_of.get(aid, aid.rsplit("-g", 1)[0])
        pb = play_of.get(gid, "")
        if pb in fam or any(gid.startswith(f"GEN-") and pb in fam for _ in [0]):
            is_hold[i] = pb in fam
        # also match playbook substring on attack id prefixes via genome_of
        is_hold[i] = pb in fam

    hold = is_hold & (y == 1)
    rest_fraud = (~is_hold) & (y == 1)
    legit = y == 0

    def _auc(mask_pos):
        m = mask_pos | legit
        if mask_pos.sum() < 5 or legit.sum() < 10:
            return None
        try:
            return round(float(roc_auc_score(y[m], p[m])), 4)
        except ValueError:
            return None

    return {
        "holdout_fraud_n": int(hold.sum()),
        "seen_fraud_n": int(rest_fraud.sum()),
        "family_holdout_auc": _auc(hold),
        "seen_family_auc": _auc(rest_fraud),
        "families": list(family_playbooks),
    }


def ablation_aucs(X: pd.DataFrame, y: np.ndarray, cut: int, seed: int = 7) -> dict:
    """Tabular vs graph vs sequence heads on the same temporal split."""
    ytr, yte = y[:cut], y[cut:]
    out = {}
    for name, cols in (
        ("tabular", [c for c in TABULAR_FEATS if c in X.columns]),
        ("graph", [c for c in GRAPH_FEATS if c in X.columns]),
        ("sequence", [c for c in SEQ_FEATS if c in X.columns]),
    ):
        if len(cols) < 2 or yte.sum() == 0:
            out[name] = None
            continue
        clf = HistGradientBoostingClassifier(
            max_iter=80, learning_rate=0.1, max_leaf_nodes=15,
            min_samples_leaf=20, random_state=seed)
        clf.fit(X.iloc[:cut][cols], ytr)
        p = clf.predict_proba(X.iloc[cut:][cols])[:, 1]
        try:
            out[name] = round(float(roc_auc_score(yte, p)), 4)
        except ValueError:
            out[name] = None
    return out


def occupant_isolation_forest(X: pd.DataFrame, y: np.ndarray, cut: int,
                              seed: int = 7) -> dict:
    """Second occupant of the tunnel — unsupervised, model-agnostic demo."""
    Xtr = X.iloc[:cut]
    yte = y[cut:]
    legit = Xtr[y[:cut] == 0]
    if len(legit) < 30 or yte.sum() == 0:
        return {"iforest_auc": None}
    iso = IsolationForest(n_estimators=80, contamination=0.02,
                          random_state=seed, n_jobs=1)
    iso.fit(legit)
    # higher score = more abnormal
    s = -iso.score_samples(X.iloc[cut:])
    try:
        auc = round(float(roc_auc_score(yte, s)), 4)
    except ValueError:
        auc = None
    return {"iforest_auc": auc, "occupant": "isolation_forest"}


def conformal_threshold(p_cal: np.ndarray, y_cal: np.ndarray,
                        fpr_budget: float) -> float:
    return FusionDetector.conformal_threshold(p_cal, y_cal, fpr_budget)


def protocol_block(
    X: pd.DataFrame, y: np.ndarray, meta: pd.DataFrame, p: np.ndarray, thr: float,
    genome_of: dict[str, str], cut: int, fpr_budget: float, target_rate: float,
    family_playbooks: tuple[str, ...] = DEFAULT_HOLD_FAMILIES,
    genomes: list | None = None, seed: int = 7,
) -> dict:
    """Single dict attached to each Red Queen history row."""
    p_te, y_te = p[cut:], y[cut:]
    br = metrics_at_base_rate(p_te, y_te, thr, target_rate, fpr_budget, seed)
    fam = family_holdout_auc(p, y, meta, genome_of, family_playbooks, genomes)
    abl = ablation_aucs(X, y, cut, seed)
    occ = occupant_isolation_forest(X, y, cut, seed)
    return {
        "lab_auc": None,  # filled by caller
        "recall_at_base_rate": br.get("recall"),
        "precision_at_base_rate": br.get("precision"),
        "fpr_at_base_rate": br.get("fpr"),
        "base_rate": br.get("fraud_rate"),
        "family_holdout_auc": fam.get("family_holdout_auc"),
        "seen_family_auc": fam.get("seen_family_auc"),
        "holdout_fraud_n": fam.get("holdout_fraud_n"),
        "ablation_auc": abl,
        "occupant_iforest_auc": occ.get("iforest_auc"),
        "headline": (
            "Report recall@base-rate and family-holdout AUC, not in-generator ROC."
        ),
    }


def occupancy_score(X: pd.DataFrame, scores: np.ndarray, labels: np.ndarray | None,
                    fpr_budget: float = 0.005) -> dict:
    """Bank brings scores; AGNI grades them (tunnel occupancy API)."""
    scores = np.asarray(scores, dtype=float)
    if labels is None:
        return {"n": int(len(scores)), "mean_score": round(float(scores.mean()), 4)}
    y = np.asarray(labels)
    thr = FusionDetector.choose_threshold(scores, y, fpr_budget)
    m = FusionDetector.evaluate(scores, y, thr, fpr_budget)
    m["n"] = int(len(y))
    return m
