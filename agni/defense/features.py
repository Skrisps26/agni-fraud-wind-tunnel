"""Feature engineering for Sentinel.

Per-transaction features blending: user behavioral baselines, velocity windows,
destination-graph shape (fan-in / forwarding - the mule signature), device
novelty, temporal encoding, and merchant risk. Pure pandas/numpy, no extra deps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = [
    "amount_log", "amt_z_user",
    "vel_10m", "vel_1h", "vel_24h", "vel_ratio_10m_24h", "interarrival_log",
    "new_dst_pair", "dst_fan_in", "dst_max_src_share", "dst_fwd_rate_24h",
    "dst_unique_src_1h", "src_new_dst_24h",
    "device_new_for_user",
    "hour_sin", "hour_cos", "off_hours",
    "kind_p2m", "rail_card", "rail_wire", "channel_agent", "channel_collect",
    "merchant_high_risk", "user_tenure_days",
]


def _per_src_velocity(df: pd.DataFrame, epochs: np.ndarray) -> tuple[np.ndarray, ...]:
    out = [np.zeros(len(df)) for _ in range(3)]
    windows = (600, 3600, 86400)
    for _, idx in df.groupby("src", sort=False).indices.items():
        idx = np.asarray(idx)
        ep = epochs[idx]
        for w_i, w in enumerate(windows):
            lo = np.searchsorted(ep, ep - w, side="left")
            hi = np.searchsorted(ep, ep, side="right")  # includes current
            out[w_i][idx] = hi - lo
    return tuple(out)


def _expanding_zscore(df: pd.DataFrame) -> np.ndarray:
    z = np.zeros(len(df))
    for _, idx in df.groupby("src", sort=False).indices.items():
        idx = np.asarray(idx)
        amt = df["amount"].values[idx]
        csum = np.cumsum(amt)
        csum2 = np.cumsum(amt * amt)
        n = np.arange(1, len(idx) + 1, dtype=float)
        prev_n = np.maximum(n - 1, 1)
        mean_prev = np.where(n > 1, (csum - amt) / prev_n, amt)
        var_prev = np.where(
            n > 2,
            np.maximum((csum2 - amt * amt) / prev_n - mean_prev ** 2, 0.0),
            0.0)
        std_prev = np.sqrt(var_prev)
        with np.errstate(divide="ignore", invalid="ignore"):
            zi = np.where((n > 1) & (std_prev > 0),
                          (amt - mean_prev) / std_prev, 0.0)
        z[idx] = np.clip(np.nan_to_num(zi), 0, 25)
    return z


def _dst_features(df: pd.DataFrame, epochs: np.ndarray) -> tuple[np.ndarray, ...]:
    fan_in = np.zeros(len(df))
    share = np.zeros(len(df))
    fwd = np.zeros(len(df))

    # outgoing epoch index per account (account acts as sender)
    out_epochs: dict[str, np.ndarray] = {}
    for s, idx in df.groupby("src", sort=False).indices.items():
        out_epochs[s] = epochs[np.asarray(idx)]

    grp = df.groupby("dst", sort=False).indices
    dst_counts = {d: len(i) for d, i in grp.items()}
    for d, idx in grp.items():
        idx = np.asarray(idx)
        n = len(idx)
        fan_in[idx] = n
        srcs = df["src"].values[idx]
        _, counts = np.unique(srcs, return_counts=True)
        share[idx] = counts.max() / n if n else 0.0
        out_ep = out_epochs.get(d)
        if out_ep is not None and len(out_ep):
            t_in = epochs[idx]
            hi = np.searchsorted(out_ep, t_in + 86400, side="right")
            lo = np.searchsorted(out_ep, t_in, side="left")
            fwd[idx] = np.clip((hi - lo) / max(dst_counts.get(d, n), 1), 0, 1)
    return fan_in, share, fwd


def _dst_unique_src_1h(df: pd.DataFrame, epochs: np.ndarray) -> np.ndarray:
    out = np.zeros(len(df))
    for _, idx in df.groupby("dst", sort=False).indices.items():
        idx = np.asarray(idx)
        ep = epochs[idx]
        srcs = df["src"].values[idx]
        for i, j in enumerate(idx):
            lo = int(np.searchsorted(ep, ep[i] - 3600, side="left"))
            out[j] = len(set(srcs[lo:i + 1]))
    return out


def _src_new_dst_24h(df: pd.DataFrame, epochs: np.ndarray) -> np.ndarray:
    out = np.zeros(len(df))
    new_pair = ~df.duplicated(["src", "dst"]).to_numpy()
    for _, idx in df.groupby("src", sort=False).indices.items():
        idx = np.asarray(idx)
        ep = epochs[idx]
        npair = new_pair[idx]
        for i, j in enumerate(idx):
            lo = int(np.searchsorted(ep, ep[i] - 86400, side="left"))
            out[j] = float(npair[lo:i + 1].sum())
    return out


def build_dataset(sim) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (features_df[FEATURES], meta_df). Rows are time-sorted."""
    df = sim.ledger.to_df()
    if df.empty:
        raise RuntimeError("empty ledger")
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.sort_values("ts").reset_index(drop=True)
    # numpy-level conversion: stable across pandas 2.x/3.x
    epochs = df["ts"].to_numpy(dtype="datetime64[s]").astype("int64")

    v10, v1h, v24 = _per_src_velocity(df, epochs)
    vel_ratio = v10 / np.maximum(v24, 1.0)
    inter = np.zeros(len(df))
    for _, idx in df.groupby("src", sort=False).indices.items():
        idx = np.asarray(idx)
        ep = epochs[idx]
        d = np.diff(ep, prepend=ep[0])
        inter[idx] = np.log1p(np.maximum(d, 0))
    amt_z = _expanding_zscore(df)
    fan_in, share, fwd = _dst_features(df, epochs)
    uniq_1h = _dst_unique_src_1h(df, epochs)
    new_dst_24 = _src_new_dst_24h(df, epochs)

    # pair novelty
    new_pair = ~df.duplicated(["src", "dst"]).to_numpy()

    # device novelty: unknown device for this consumer (synthetic accts: always new)
    known_dev: dict[str, set[str]] = {}
    for c in sim.pop.consumers:
        known_dev[c.id] = set(c.device_ids)
    dev_new = np.array([
        t.device_id not in known_dev.get(t.src, set())
        for t in df.itertuples()
    ], dtype=float)

    hours = df["ts"].dt.hour.to_numpy(dtype=float)
    off_hours = ((hours < 6) | (hours >= 23)).astype(float)

    merchants = sim.pop.merchant_by_id
    merch_hr = np.array([
        1.0 if (t.kind == "p2m" and t.merchant_id in merchants
                and merchants[t.merchant_id].is_high_risk) else 0.0
        for t in df.itertuples()])

    first_seen = {}
    for c in sim.pop.consumers:
        first_seen[c.id] = -float(c.tenure_days) * 86400
    tenure = np.array([
        max((epochs[i] - sim.start.timestamp()) - first_seen.get(t.src, 0.0), 0.0) / 86400
        for i, t in enumerate(df.itertuples())])

    X = pd.DataFrame({
        "amount_log": np.log1p(df["amount"].to_numpy()),
        "amt_z_user": amt_z,
        "vel_10m": v10.astype(float), "vel_1h": v1h.astype(float),
        "vel_24h": v24.astype(float),
        "vel_ratio_10m_24h": vel_ratio.astype(float),
        "interarrival_log": inter.astype(float),
        "new_dst_pair": new_pair.astype(float),
        "dst_fan_in": np.log1p(fan_in),
        "dst_max_src_share": share,
        "dst_fwd_rate_24h": fwd,
        "dst_unique_src_1h": np.log1p(uniq_1h),
        "src_new_dst_24h": new_dst_24.astype(float),
        "device_new_for_user": dev_new,
        "hour_sin": np.sin(2 * np.pi * hours / 24),
        "hour_cos": np.cos(2 * np.pi * hours / 24),
        "off_hours": off_hours,
        "kind_p2m": (df["kind"] == "p2m").to_numpy().astype(float),
        "rail_card": (df["rail"] == "card").to_numpy().astype(float),
        "rail_wire": (df["rail"] == "wire").to_numpy().astype(float),
        "channel_agent": (df["channel"] == "agent").to_numpy().astype(float),
        "channel_collect": (df["channel"].isin(["upi_collect", "collect"])).to_numpy().astype(float),
        "merchant_high_risk": merch_hr,
        "user_tenure_days": tenure,
    })[FEATURES]

    meta = pd.DataFrame({
        "txn_id": df["txn_id"], "ts": df["ts"], "src": df["src"],
        "dst": df["dst"], "attack_id": df["attack_id"],
        "is_fraud": df["is_fraud"].astype(int), "amount": df["amount"],
    })
    return X.replace([np.inf, -np.inf], 0.0).fillna(0.0), meta
