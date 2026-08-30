"""Smoke tests: deterministic twin, mini end-to-end loop, API contract."""

from __future__ import annotations

import numpy as np

from agni.config import Config
from agni.loop.redqueen import run_loop
from agni.twin.population import Population


def _mini_cfg() -> Config:
    return Config(seed=11, consumers=260, merchants=60, days=6,
                  runs_per_genome=2, benign_msg_cap=600, generations=2)


def test_population_reproducible():
    r1 = np.random.default_rng(42)
    r2 = np.random.default_rng(42)
    p1 = Population.generate(50, 20, r1)
    p2 = Population.generate(50, 20, r2)
    assert [c.id for c in p1.consumers] == [c.id for c in p2.consumers]
    assert all(c.avg_amount > 0 for c in p1.consumers)


def test_end_to_end_mini_loop():
    cfg = _mini_cfg()
    result, extra = run_loop(cfg, verbose=False)
    assert len(result.history) == cfg.generations
    h0, h1 = result.history[0], result.history[-1]
    for key in ("roc_auc", "precision", "recall", "f1", "fpr", "fidelity_mean"):
        assert key in h0 and key in h1
    # detector must beat random on the holdout
    assert h1["roc_auc"] >= 0.62
    # false-positive budget enforced by threshold policy or near it
    assert h1["fpr"] <= cfg.fpr_budget * 3
    assert result.total_attack_txns > 0
    assert len(result.genomes_final) >= 1


def test_api_state_and_contract():
    from fastapi.testclient import TestClient
    from agni.server.main import app
    client = TestClient(app)
    r = client.get("/api/state")
    assert r.status_code == 200
    body = r.json()
    for key in ("history", "genomes", "alerts", "tte_generations", "mule_graph", "atlas"):
        assert key in body
    assert client.get("/health").status_code == 200
    r2 = client.post("/api/loop/run", json={"generations": 1})
    assert r2.status_code == 200
    assert r2.json()["ok"] is True
