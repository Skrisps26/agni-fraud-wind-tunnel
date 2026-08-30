"""Critic Agent — reasons about evasion strategies for the Agent Council."""

from __future__ import annotations

from agni.genome.schema import AttackGenome
from agni.llm.client import chat_text, llm_available
from agni.llm.prompts import CRITIC_SYSTEM


def critic_brief(genome: AttackGenome, det_rate: float,
                 blind_spots: list[str], frozen_auc: float | None,
                 generation: int) -> str:
    """Human-readable Critic message for the UI."""
    feats = ", ".join(blind_spots) if blind_spots else "none identified"
    frozen = f"{frozen_auc:.3f}" if frozen_auc is not None else "n/a"
    offline = (
        f"[Critic gen {generation}] {genome.id} det_rate={det_rate:.0%}, "
        f"frozen_AUC={frozen}. Blind spots: {feats}. "
        "Mutating toward slower velocity and smaller amounts."
    )
    if not llm_available():
        return offline

    user = (
        f"Generation: {generation}\n"
        f"Genome: {genome.id} — {genome.name}\n"
        f"Playbook: {genome.playbook}\n"
        f"Detection rate: {det_rate:.2%}\n"
        f"Frozen defender AUC on new attacks: {frozen}\n"
        f"Blind-spot features: {feats}\n"
        f"Params: {genome.params}"
    )
    reply = chat_text(CRITIC_SYSTEM, user, namespace="critic")
    if reply:
        return f"[Critic gen {generation}] {reply}"
    return offline
