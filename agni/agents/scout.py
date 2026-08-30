"""Scout Agent — fills atlas holes with compiled playbooks, not param clones."""

from __future__ import annotations

import json
from pathlib import Path

from agni.foundry.base import REGISTRY
from agni.foundry.sandbox import compile_or_bind
from agni.genome.atlas import empty_cell_for_scout
from agni.genome.schema import (
    AttackGenome, Channel, Citation, GenAICapability, KillChainStage,
    Rail, Surface, Victim,
)
from agni.llm.client import chat_json, llm_available
from agni.llm.prompts import SCOUT_SYSTEM

INTEL = Path(__file__).parent / "intel" / "snippets.json"


def _intel_block() -> str:
    snippets = json.loads(INTEL.read_text())
    return "\n".join(f"- {s['title']}: {s['text']}" for s in snippets)


def _cite() -> list[Citation]:
    return [Citation(source="AGNI intel snippets", note="Public TTP seed, not dark-web.")]


def _fill_hole(generation: int, genomes: list[AttackGenome]) -> tuple[AttackGenome | None, str]:
    hole = empty_cell_for_scout(genomes)
    key, note = compile_or_bind(generation, hole, genomes)
    rail = Rail.UPI
    surface = Surface.SOCIAL_ENGINEERING
    cap = GenAICapability.TEXT_GENERATION
    if hole:
        try:
            rail = Rail(hole["rail"]) if hole["rail"] in Rail._value2member_map_ else Rail.UPI
        except Exception:
            rail = Rail.UPI
        try:
            surface = Surface(hole["surface"])
        except Exception:
            pass
        try:
            cap = GenAICapability(hole["capability"])
        except Exception:
            pass
    gid = f"GEN-S{generation:03d}"
    genome = AttackGenome(
        id=gid,
        name=f"Scout compile gen {generation}",
        playbook=key,
        summary=(hole or {}).get("note") or "Compiled Foundry playbook from atlas hole.",
        rails=[rail],
        surfaces=[surface],
        capabilities=[cap],
        ttps=["scout_compiled", "upi_collect_drip"],
        origin="scout",
        tier="C",
        generation_born=generation,
        family_id=gid,
        channels=[Channel.UPI_COLLECT],
        victims=[Victim.CONSUMER],
        stages=[KillChainStage.CONTACT, KillChainStage.PHISH, KillChainStage.TRANSFER],
        citations=_cite(),
        executable=True,
        hole=(hole or {}).get("note", ""),
        params={"n_attacks": 3},
    )
    msg = (
        f"[Scout gen {generation}] Compiled playbook '{key}' "
        f"({note}). Atlas hole: {genome.hole or 'none'}."
    )
    return genome, msg


def scout_propose(generation: int, blind_spots: dict[str, list[str]],
                  weakest_id: str | None,
                  genomes: list[AttackGenome]) -> tuple[AttackGenome | None, str]:
    existing_ids = {g.id for g in genomes}
    playbooks = sorted(REGISTRY.keys())

    if not llm_available():
        return _fill_hole(generation, genomes)

    hole = empty_cell_for_scout(genomes)
    blind_summary = ", ".join(
        f"{gid}: {feats}" for gid, feats in list(blind_spots.items())[:5]
    ) or "none yet"
    user = (
        f"Generation: {generation}\n"
        f"Allowed playbooks: {', '.join(playbooks)}\n"
        f"Atlas hole: {hole}\n"
        f"Defender blind spots: {blind_summary}\n"
        f"Weakest genome: {weakest_id}\n"
        f"Threat intel:\n{_intel_block()}\n"
        f"Propose id GEN-S{generation:03d}. Prefer filling the atlas hole. "
        f"If you cannot, still return JSON."
    )
    data = chat_json(SCOUT_SYSTEM, user, namespace="scout")
    if not data:
        return _fill_hole(generation, genomes)

    data.setdefault("origin", "scout")
    data.setdefault("tier", "C")
    data["generation_born"] = generation
    key, _ = compile_or_bind(generation, hole, genomes)
    data["playbook"] = key
    data["executable"] = True
    data["hole"] = (hole or {}).get("note", "")
    try:
        genome = AttackGenome.model_validate(data)
        if genome.id in existing_ids:
            genome = genome.model_copy(update={"id": f"GEN-S{generation:03d}"})
        genome = genome.model_copy(update={"playbook": key, "citations": _cite()})
        msg = (
            f"[Scout gen {generation}] Discovered '{genome.name}' "
            f"and compiled playbook {key}."
        )
        return genome, msg
    except Exception:
        return _fill_hole(generation, genomes)
