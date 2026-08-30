"""Protocol, atlas, and Scout compile smoke tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from agni.defense.model import FusionDetector
from agni.eval.harness import downsample_to_base_rate, occupancy_score
from agni.foundry.sandbox import compile_or_bind
from agni.genome.atlas import coverage_matrix
from agni.genome.schema import load_genomes


def test_atlas_families_not_json_count():
    genomes = load_genomes()
    cov = coverage_matrix(genomes)
    assert cov["n_tier_a"] == 13
    assert cov["n_families"] >= 13
    assert cov["n_genomes"] == len(genomes)
    assert cov["holes"]
    assert cov["diversity"]["n_variants"] >= 0
    assert "not a unique-engine" in cov["disclaimer"].lower() or "not a unique" in cov["disclaimer"]


def test_base_rate_downsample():
    rng = np.random.default_rng(0)
    y = np.array([0] * 1000 + [1] * 250)
    p = rng.random(len(y))
    yb, pb = downsample_to_base_rate(y, p, 0.002, rng)
    assert abs(yb.mean() - 0.002) < 0.003
    assert len(yb) == len(pb)


def test_conformal_and_occupancy():
    rng = np.random.default_rng(1)
    y = np.concatenate([np.zeros(400, dtype=int), np.ones(40, dtype=int)])
    p = np.concatenate([rng.uniform(0, 0.4, 400), rng.uniform(0.6, 1, 40)])
    thr = FusionDetector.conformal_threshold(p, y, 0.005)
    assert 0 < thr < 1
    m = occupancy_score(None, p, y, 0.05)
    assert "roc_auc" in m


def test_scout_compiles_playbook():
    key, note = compile_or_bind(99, {"rail": "aeps", "note": "test hole"}, [])
    assert key in ("scout_compiled_99",)
    from agni.foundry.base import REGISTRY
    assert key in REGISTRY
