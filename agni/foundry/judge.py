"""Fidelity Judge: scores how closely simulated attacks resemble real payment
behavior before they are used for training.

Reference distributions, in order of preference:
  1. REAL anchor data (data/anchor/*transaction*.csv, e.g. IEEE-CIS/Vesta)
     - kills the circularity of scoring simulations against simulations
  2. fallback: the twin's own legitimate traffic (offline mode)

Deterministic components:
  - amount distribution similarity (KS statistic vs reference)
  - hour-of-day distribution similarity (KS)
  - velocity plausibility (no physically impossible bursts)
  - artifact diversity (unique-text ratio)

Optional LLM component scores scam-text realism when Config.llm_enabled.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


@dataclass
class FidelityReport:
    attack_id: str
    genome_id: str
    amount_similarity: float
    hour_similarity: float
    velocity_plausible: float
    text_diversity: float
    overall: float


def _legit_reference(df: pd.DataFrame) -> pd.DataFrame:
    legit = df[df.is_fraud == 0]
    p2p = legit[legit.kind == "p2p"]
    return p2p if len(p2p) >= 200 else legit


def judge_attack(df: pd.DataFrame, artifacts: pd.DataFrame,
                 attack_id: str, genome_id: str,
                 anchor: dict | None = None) -> FidelityReport:
    atk = df[df.attack_id == attack_id]
    if atk.empty:
        return FidelityReport(attack_id, genome_id, 0.0, 0.0, 1.0, 0.0, 0.0)

    # --- amounts -------------------------------------------------------------
    if anchor is not None and len(anchor.get("amount", [])):
        d_amt = float(ks_2samp(atk.amount.values, anchor["amount"]).statistic)
        amount_sim = max(0.0, 1.0 - d_amt)
    else:
        ref = _legit_reference(df)
        same_kind = ref[ref.kind.isin(atk.kind.unique())]
        cmp_df = same_kind if len(same_kind) >= 100 else ref
        if len(cmp_df):
            d_amt = float(ks_2samp(atk.amount.values, cmp_df.amount.values).statistic)
            amount_sim = max(0.0, 1.0 - d_amt)
        else:
            amount_sim = 0.5

    # --- hours of day ----------------------------------------------------------
    if anchor is not None and len(anchor.get("hour", [])):
        hour_ref = anchor["hour"]
    else:
        hour_ref = df.ts.dt.hour.values
    d_hour = float(ks_2samp(atk.ts.dt.hour.values, hour_ref).statistic)
    hour_sim = max(0.0, 1.0 - d_hour)

    # --- velocity plausibility ----------------------------------------------
    per_min = atk.set_index("ts").groupby("src").resample("1min").size()
    mx = float(per_min.max()) if len(per_min) else 1.0
    vel_ok = 1.0 if mx <= 6 else max(0.0, 1.0 - (mx - 6) / 10)

    # --- text diversity ---------------------------------------------------------
    arts = artifacts[artifacts.attack_id == attack_id] \
        if isinstance(artifacts, pd.DataFrame) and len(artifacts) else None
    if arts is not None and len(arts):
        uniq = arts.text.nunique() / len(arts)
        text_div = float(min(uniq * 1.15, 1.0))
    else:
        text_div = 0.5

    overall = float(np.average([amount_sim, hour_sim, vel_ok, text_div],
                               weights=[0.35, 0.25, 0.2, 0.2]))
    return FidelityReport(attack_id, genome_id, round(amount_sim, 4),
                          round(hour_sim, 4), round(vel_ok, 4),
                          round(text_div, 4), round(overall, 4))


def judge_all(sim, genome_of: dict[str, str] | None = None,
              anchor: dict | None = None) -> list[FidelityReport]:
    """Score every attack in the ledger.
    genome_of maps attack_id -> genome id; anchor = real-data marginals."""
    df = sim.ledger.to_df()
    df["ts"] = pd.to_datetime(df["ts"])
    arts = sim.ledger.artifacts_df()
    if len(arts):
        arts["ts"] = pd.to_datetime(arts["ts"])
    genome_of = genome_of or {}
    reports = []
    for aid in sorted(a for a in df.attack_id.unique() if a):
        gid = genome_of.get(aid, aid.rsplit("-", 1)[0] if "-" in aid else aid)
        reports.append(judge_attack(df, arts, aid, gid, anchor=anchor))
    return reports
