"""Fraud Genome Atlas — coverage matrix and diversity score (Pillar 1)."""

from __future__ import annotations

from agni.foundry.base import REGISTRY
from agni.foundry import playbooks as _playbooks  # noqa: F401
from agni.genome.schema import (
    AttackGenome, GenAICapability, Rail, Surface, Victim, load_genomes,
)

# Focused atlas axes (not a 10^5 cartesian product).
ATLAS_RAILS = (Rail.UPI, Rail.CARD, Rail.WIRE, Rail.WALLET, Rail.AEPS, Rail.RUPAY, Rail.BNPL)
ATLAS_SURFACES = tuple(Surface)
ATLAS_CAPS = tuple(GenAICapability)

# Documented holes a bank would still want compiled.
PRIORITY_HOLES = [
    {"rail": "aeps", "surface": "onboarding_kyc", "capability": "deepfake_video",
     "victim": "consumer", "note": "AEPS + deepfake liveness — playbook not compiled."},
    {"rail": "bnpl", "surface": "behavioral", "capability": "agent_orchestration",
     "victim": "consumer", "note": "BNPL agent-orchestrated bust-out — playbook not compiled."},
    {"rail": "ussd", "surface": "social_engineering", "capability": "text_generation",
     "victim": "consumer", "note": "USSD social-engineering — playbook not compiled."},
    {"rail": "upi", "surface": "infrastructure", "capability": "agent_orchestration",
     "victim": "merchant", "note": "Dispute/chargeback agent loop — playbook not compiled."},
]


def _cell_key(rail: str, surface: str, cap: str) -> str:
    return f"{rail}|{surface}|{cap}"


def coverage_matrix(genomes: list[AttackGenome] | None = None) -> dict:
    """Filled vs empty cells. Empty cells are first-class Identify output."""
    genomes = genomes or load_genomes()
    filled: dict[str, list[str]] = {}
    for g in genomes:
        if not g.executable:
            continue
        for r in g.rails:
            for s in g.surfaces:
                for c in g.capabilities:
                    k = _cell_key(r.value, s.value, c.value)
                    filled.setdefault(k, []).append(g.id)

    cells = []
    n_total = 0
    n_hit = 0
    for r in ATLAS_RAILS:
        for s in ATLAS_SURFACES:
            for c in ATLAS_CAPS:
                n_total += 1
                k = _cell_key(r.value, s.value, c.value)
                ids = filled.get(k, [])
                if ids:
                    n_hit += 1
                cells.append({
                    "rail": r.value, "surface": s.value, "capability": c.value,
                    "genomes": ids[:6], "filled": bool(ids),
                })

    holes = []
    for h in PRIORITY_HOLES:
        k = _cell_key(h["rail"], h["surface"], h["capability"])
        if k not in filled:
            holes.append(h)

    families = sorted({g.family() for g in genomes})
    return {
        "n_genomes": len(genomes),
        "n_families": len(families),
        "n_tier_a": sum(1 for g in genomes if g.tier == "A"),
        "n_playbooks": len(REGISTRY) or len({g.playbook for g in genomes}),
        "cells_total": n_total,
        "cells_filled": n_hit,
        "coverage": round(n_hit / max(n_total, 1), 4),
        "diversity": diversity_score(genomes),
        "families": families,
        "holes": holes,
        "cells": cells,
        "disclaimer": (
            "Coverage is a taxonomy score, not a unique-engine count. "
            "Tier-B files are variants. Empty cells are documented gaps."
        ),
    }


def diversity_score(genomes: list[AttackGenome]) -> dict:
    """Families + TTP Jaccard mean distance. Not len(json files)."""
    fam = {g.family() for g in genomes}
    playbooks = {g.playbook for g in genomes}
    children = [g for g in genomes if g.parent_ids]
    ttps = [set(g.ttps or [g.playbook]) for g in genomes if g.tier == "A"]
    dist = 0.0
    n = 0
    for i in range(len(ttps)):
        for j in range(i + 1, len(ttps)):
            u = len(ttps[i] | ttps[j])
            inter = len(ttps[i] & ttps[j])
            dist += 1.0 - (inter / u if u else 1.0)
            n += 1
    return {
        "n_families": len(fam),
        "n_playbooks": len(playbooks),
        "n_variants": len(children),
        "mean_ttp_distance": round(dist / max(n, 1), 4),
        "score": round(
            0.45 * min(len(fam) / 20, 1) + 0.35 * (dist / max(n, 1)) + 0.20 * min(len(playbooks) / 16, 1),
            4,
        ),
    }


def empty_cell_for_scout(genomes: list[AttackGenome]) -> dict | None:
    cov = coverage_matrix(genomes)
    return cov["holes"][0] if cov["holes"] else None


def main() -> None:
    import json
    from agni.foundry.base import build_playbook  # noqa: F401 — register
    from agni.foundry import playbooks as _pb  # noqa: F401
    print(json.dumps({k: v for k, v in coverage_matrix().items() if k != "cells"}, indent=2))


if __name__ == "__main__":
    main()
