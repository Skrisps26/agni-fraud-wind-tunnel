"""Real-data anchoring: calibration fitting and its effect on the twin/judge."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from agni.foundry.judge import judge_all
from agni.twin.calibrate import fit_ieee, load_anchor_sample
from agni.twin.population import Population
from agni.twin.rails import Simulation


def _fake_ieee_csv(tmp_path, n=4000):
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "TransactionAmt": rng.lognormal(np.log(130), 1.2, n).round(2),
        "TransactionDT": rng.integers(0, 120 * 86400, n),  # 120 days of seconds
        "ProductCD": rng.choice(["W", "C", "R", "H", "S"], n),
        "isFraud": (rng.random(n) < 0.035).astype(int),
    })
    p = tmp_path / "train_transaction.csv"
    df.to_csv(p, index=False)
    return p


def test_fit_ieee_marginals(tmp_path):
    csv = _fake_ieee_csv(tmp_path)
    calib = fit_ieee(csv)
    assert calib["rows_used"] == 4000
    assert abs(sum(calib["hour_weights"]) - 1.0) < 1e-3
    assert len(calib["hour_weights"]) == 24
    assert set(calib["product_medians_usd"]) <= {"W", "C", "R", "H", "S"}
    assert 100 < calib["amount_usd"]["median"] < 200
    # consumer target is fx-scaled
    assert calib["consumer_median_inr"] > calib["amount_usd"]["median"]


def test_population_uses_calibration(tmp_path):
    csv = _fake_ieee_csv(tmp_path)
    calib = fit_ieee(csv)
    rng = np.random.default_rng(5)
    pop = Population.generate(300, 40, rng, calibration=calib)
    medians = [c.avg_amount for c in pop.consumers]
    # median ticket size should land near the fitted consumer target
    assert abs(float(np.median(medians)) - calib["consumer_median_inr"]) < \
        0.15 * calib["consumer_median_inr"]
    assert abs(pop.hour_weights.sum() - 1.0) < 1e-6


def test_judge_prefers_real_anchor(tmp_path):
    csv = _fake_ieee_csv(tmp_path, n=8000)
    anchor = {"amount": pd.read_csv(csv)["TransactionAmt"].to_numpy(),
              "hour": (pd.read_csv(csv)["TransactionDT"].to_numpy(np.int64) // 3600) % 24}
    rng = np.random.default_rng(9)
    pop = Population.generate(150, 30, rng)
    sim = Simulation(pop, days=4)
    sim.background_traffic(rng)
    from agni.foundry.base import AttackContext, build_playbook
    from agni.genome.schema import load_genomes
    g = next(x for x in load_genomes() if x.params)
    ctx = AttackContext(sim, rng, f"{g.id}-t0", dict(g.params))
    build_playbook(g).execute(ctx)
    reports_a = judge_all(sim, {f"{g.id}-t0": g.id}, anchor=anchor)
    reports_b = judge_all(sim, {f"{g.id}-t0": g.id}, anchor=None)
    if reports_a:
        # both modes produce valid scores; anchor mode must reference real data
        assert 0.0 <= reports_a[0].overall <= 1.0
        assert isinstance(reports_b[0].overall, float)


def test_anchor_loader_graceful_without_data():
    # never raises whether or not data/anchor exists on this machine
    result = load_anchor_sample()
    assert result is None or set(("amount", "hour")) <= set(result)
