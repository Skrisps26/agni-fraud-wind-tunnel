"""Scout Agent — discovers new attack vectors from threat intel + blind spots."""

from __future__ import annotations

import json
from pathlib import Path

from agni.foundry.base import REGISTRY
from agni.genome.schema import AttackGenome, propose_variant
from agni.llm.client import chat_json, llm_available
from agni.llm.prompts import SCOUT_SYSTEM

INTEL = Path(__file__).parent / "intel" / "snippets.json"


def _intel_block() -> str:
    snippets = json.loads(INTEL.read_text())
    return "\n".join(f"- {s['title']}: {s['text']}" for s in snippets)


def _offline_scout(generation: int, weakest_id: str | None,
                   genomes: list[AttackGenome]) -> tuple[AttackGenome | None, str]:
    if not weakest_id:
        return None, f"[Scout gen {generation}] Offline — no weak vector to branch from."
    base = next((g for g in genomes if g.id == weakest_id), None)
    if base is None:
        base = genomes[0] if genomes else None
    if base is None:
        return None, f"[Scout gen {generation}] Offline — empty genome library."
    child = propose_variant(base, None, generation)
    child = child.model_copy(update={
        "id": f"GEN-S{generation:03d}",
        "name": f"{base.name} (Scout branch)",
        "origin": "scout",
        "tier": "C",
    })
    return child, (
        f"[Scout gen {generation}] Offline branch from {base.id} → {child.id} "
        f"({child.playbook})."
    )


def scout_propose(generation: int, blind_spots: dict[str, list[str]],
                  weakest_id: str | None,
                  genomes: list[AttackGenome]) -> tuple[AttackGenome | None, str]:
    """Return (new genome or None, agent message for UI)."""
    existing_ids = {g.id for g in genomes}
    playbooks = sorted(REGISTRY.keys())
    if not llm_available():
        return _offline_scout(generation, weakest_id, genomes)

    blind_summary = ", ".join(
        f"{gid}: {feats}" for gid, feats in list(blind_spots.items())[:5]
    ) or "none yet"
    user = (
        f"Generation: {generation}\n"
        f"Allowed playbooks: {', '.join(playbooks)}\n"
        f"Defender blind spots: {blind_summary}\n"
        f"Weakest genome: {weakest_id}\n"
        f"Threat intel:\n{_intel_block()}\n"
        f"Propose id GEN-S{generation:03d} not in existing set."
    )
    data = chat_json(SCOUT_SYSTEM, user, namespace="scout")
    if not data:
        return _offline_scout(generation, weakest_id, genomes)

    data.setdefault("origin", "scout")
    data.setdefault("tier", "C")
    data["generation_born"] = generation
    if data.get("playbook") not in playbooks:
        data["playbook"] = playbooks[0]
    try:
        genome = AttackGenome.model_validate(data)
        if genome.id in existing_ids:
            genome = genome.model_copy(update={"id": f"GEN-S{generation:03d}"})
        msg = (
            f"[Scout gen {generation}] Discovered '{genome.name}' "
            f"({genome.playbook}) targeting {', '.join(r.value for r in genome.rails)}."
        )
        return genome, msg
    except Exception as exc:
        return _offline_scout(generation, weakest_id, genomes)
