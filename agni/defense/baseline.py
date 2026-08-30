"""Rules-only baseline detector for comparison against Sentinel."""

from __future__ import annotations

import numpy as np
import pandas as pd

from agni.defense.features import FEATURES, build_dataset


def rules_predict(X: pd.DataFrame) -> np.ndarray:
    """Conservative static rules mimicking legacy bank velocity/amount thresholds.
    Deliberately misses slow-drip, behavioral-mimicry, and evolved attacks."""
    pred = np.zeros(len(X), dtype=int)
    if "vel_10m" in X.columns:
        pred |= (X["vel_10m"].to_numpy() > 10).astype(int)
    if "vel_1h" in X.columns:
        pred |= (X["vel_1h"].to_numpy() > 15).astype(int)
    if all(c in X.columns for c in ("new_dst_pair", "amt_z_user", "amount_log")):
        pred |= (
            (X["new_dst_pair"] > 0)
            & (X["amt_z_user"] > 4.0)
            & (X["amount_log"] > 9.5)
        ).to_numpy().astype(int)
    if all(c in X.columns for c in ("off_hours", "rail_wire")):
        pred |= (
            (X["off_hours"] > 0) & (X["rail_wire"] > 0) & (X["amount_log"] > 10)
        ).to_numpy().astype(int)
    return pred


def evaluate_baseline(sim, holdout_cut: float = 0.8) -> dict:
    """Recall/precision on fraud txns in test holdout."""
    X, meta = build_dataset(sim)
    y = meta["is_fraud"].to_numpy()
    cut = int(len(meta) * holdout_cut)
    X_te, y_te = X.iloc[cut:], y[cut:]
    if not (y_te == 1).any():
        return {"baseline_recall": 0.0, "baseline_precision": 0.0, "baseline_f1": 0.0}
    pred = rules_predict(X_te)
    tp = int(((pred == 1) & (y_te == 1)).sum())
    fp = int(((pred == 1) & (y_te == 0)).sum())
    fn = int(((pred == 0) & (y_te == 1)).sum())
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    return {
        "baseline_recall": round(rec, 4),
        "baseline_precision": round(prec, 4),
        "baseline_f1": round(f1, 4),
    }


def vector_det_rates(meta: pd.DataFrame, p_all: np.ndarray, thr: float,
                     genome_of: dict[str, str]) -> dict[str, float]:
    """Per-genome detection rate for heatmap."""
    mask = meta["attack_id"].to_numpy() != ""
    if not mask.any():
        return {}
    sub = pd.DataFrame({
        "gid": [genome_of.get(a, a.rsplit("-g", 1)[0]) for a in meta["attack_id"][mask]],
        "hit": (p_all[mask] >= thr).astype(float),
    })
    return {k: round(float(v), 4) for k, v in sub.groupby("gid")["hit"].mean().items()}
