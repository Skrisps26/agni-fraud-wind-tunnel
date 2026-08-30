"""Real-data anchoring: fit the twin's statistical skeleton from a real,
public transaction dataset (IEEE-CIS/Vesta via Kaggle) instead of hand-priors.

Pipeline:
  1. Drop `train_transaction.csv` into data/anchor/   (see data/README.md)
  2. `python -m agni.twin.calibrate`                  -> agni/twin/calibration.json
  3. Red Queen loop auto-detects calibration.json and the anchor CSV:
     - Population ticket sizes + hour profiles come from fitted params
     - Fidelity Judge compares attacks against REAL marginals (KS)

No raw data is committed: calibration.json stores only derived statistics.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ANCHOR_DIR = ROOT / "data" / "anchor"
CALIB_PATH = Path(__file__).resolve().parent / "calibration.json"

DEFAULT_USD_INR = 83.0


# --------------------------------------------------------------------- utils
def _lognorm_params(amounts: np.ndarray) -> dict:
    a = np.log(np.maximum(np.asarray(amounts, dtype=float), 0.01))
    return {"median": round(float(np.exp(a.mean())), 4),
            "sigma": round(float(a.std()), 4),
            "n": int(len(a))}


def _hour_profile(dt_seconds: np.ndarray) -> list[float]:
    """Hour-of-day shape from TransactionDT. NOTE: Vesta's epoch origin and
    timezone are undisclosed - we reuse the SHAPE, not absolute clock hours."""
    h = (np.asarray(dt_seconds, dtype=np.int64) // 3600) % 24
    counts = np.bincount(h, minlength=24).astype(float)
    s = counts.sum()
    return [round(float(c / s), 5) for c in counts] if s else [1 / 24] * 24


# ------------------------------------------------------------------ fitting
def fit_ieee(train_csv: Path, usd_inr: float = DEFAULT_USD_INR) -> dict:
    """Fit marginals from IEEE-CIS train_transaction.csv (needs columns
    TransactionAmt, TransactionDT, ProductCD, isFraud)."""
    df = pd.read_csv(train_csv, usecols=["TransactionAmt", "TransactionDT",
                                         "ProductCD", "isFraud"])
    amt = df["TransactionAmt"].to_numpy(dtype=float)
    return {
        "amount_usd": _lognorm_params(amt),
        # currency-normalized consumer ticket-size target for the twin (INR)
        "consumer_median_inr": round(float(np.exp(np.log(amt).mean()) * usd_inr), 2),
        "hour_weights": _hour_profile(df["TransactionDT"].to_numpy()),
        "product_medians_usd": {
            str(k): round(float(v), 4)
            for k, v in df.groupby("ProductCD")["TransactionAmt"].median().items()
        },
        "fraud_rate_observed": round(float(df["isFraud"].mean()), 5),
        "rows_used": int(len(df)),
        "source": train_csv.name,
        "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notes": [
            "Vesta TransactionDT epoch/timezone undisclosed; hour shape reused only",
            "train set oversamples fraud (~3.5%) vs production rates; not a base rate",
            f"fx assumption USD->INR = {usd_inr}",
        ],
    }


def build(anchor_csv: Path | None = None, out: Path | None = None,
          usd_inr: float | None = None) -> dict | None:
    csv = anchor_csv or next(iter(sorted(ANCHOR_DIR.glob("*ransaction*.csv"))), None)
    if csv is None or not csv.exists():
        return None
    fx = usd_inr if usd_inr is not None else float(
        os.environ.get("AGNI_USD_INR", DEFAULT_USD_INR))
    calib = fit_ieee(csv, usd_inr=fx)
    dest = out or CALIB_PATH
    dest.write_text(json.dumps(calib, indent=1))
    return calib


# ------------------------------------------------------------------- loading
def load_calibration() -> dict | None:
    try:
        return json.loads(CALIB_PATH.read_text())
    except Exception:
        return None


_ANCHOR_CACHE: dict = {}


def load_anchor_sample(max_rows: int = 20000) -> dict | None:
    """Raw anchor marginals for the Fidelity Judge (amounts + hours)."""
    global _ANCHOR_CACHE
    if "_v" in _ANCHOR_CACHE:
        return _ANCHOR_CACHE["_v"] or None
    csv = next(iter(sorted(ANCHOR_DIR.glob("*ransaction*.csv"))), None)
    if csv is None or not csv.exists():
        _ANCHOR_CACHE["_v"] = None
        return None
    df = pd.read_csv(csv, usecols=["TransactionAmt", "TransactionDT"])
    if len(df) > max_rows:
        df = df.sample(max_rows, random_state=0)
    fx = float(os.environ.get("AGNI_USD_INR", DEFAULT_USD_INR))
    _ANCHOR_CACHE["_v"] = {
        "amount": df["TransactionAmt"].to_numpy(dtype=float) * fx,
        "hour": ((df["TransactionDT"].to_numpy(dtype=np.int64) // 3600) % 24),
        "source": csv.name,
        "fx": fx,
        "unit": "INR",
    }
    return _ANCHOR_CACHE["_v"]


if __name__ == "__main__":
    calib = build()
    if calib is None:
        print(f"no anchor CSV found in {ANCHOR_DIR} - see data/README.md")
    else:
        print(f"wrote {CALIB_PATH}: rows={calib['rows_used']}, "
              f"median=${calib['amount_usd']['median']}, "
              f"consumer target={calib['consumer_median_inr']} INR")
