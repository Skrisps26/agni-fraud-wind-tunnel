"""Machine-readable "attack genome" schema - the Fraud Genome (Pillar 1: Identify).

Each genome is one GenAI-enabled payment-fraud vector encoded as structured data:
preconditions, rails, surfaces, capabilities, TTPs, detector-facing observables,
and parameters that compile into an executable playbook in the Foundry.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class Rail(str, Enum):
    CARD = "card"
    UPI = "upi"
    WIRE = "wire"
    WALLET = "wallet"


class Surface(str, Enum):
    ONBOARDING_KYC = "onboarding_kyc"
    SOCIAL_ENGINEERING = "social_engineering"
    CUSTOMER_SUPPORT = "customer_support"
    AGENTIC_CHECKOUT = "agentic_checkout"
    BEHAVIORAL = "behavioral"
    INFRASTRUCTURE = "infrastructure"


class GenAICapability(str, Enum):
    VOICE_CLONE = "voice_clone"
    DEEPFAKE_VIDEO = "deepfake_video"
    TEXT_GENERATION = "text_generation"
    DOCUMENT_FORGERY = "document_forgery"
    IMAGE_GENERATION = "image_generation"
    AGENT_ORCHESTRATION = "agent_orchestration"


class Observable(BaseModel):
    """An artifact or statistical signal a defender could detect."""

    name: str
    description: str
    signal_strength: float = Field(ge=0.0, le=1.0)


class AttackGenome(BaseModel):
    id: str
    name: str
    playbook: str  # key in agni.foundry.registry
    summary: str
    rails: list[Rail]
    surfaces: list[Surface]
    capabilities: list[GenAICapability]
    ttps: list[str] = Field(default_factory=list)
    observables: list[Observable] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    origin: Literal["seed", "critic", "scout"] = "seed"
    parent_ids: list[str] = Field(default_factory=list)
    generation_born: int = 0
    tier: Literal["A", "B", "C"] = "B"


SEED_DIR = Path(__file__).parent / "seed"


def load_genomes(directory: Path | None = None) -> list[AttackGenome]:
    """Load and validate all seed genomes shipped with the repo."""
    d = directory or SEED_DIR
    genomes = []
    for p in sorted(d.glob("*.json")):
        genomes.append(AttackGenome.model_validate(json.loads(p.read_text())))
    if not genomes:
        raise RuntimeError(f"no seed genomes found in {d}")
    return genomes


def clone_with_params(g: AttackGenome, overrides: dict, generation: int) -> AttackGenome:
    """Evolutionary mutation: new genome object with merged params and lineage."""
    params = {**g.params, **overrides}
    return g.model_copy(
        update={
            "params": params,
            "generation_born": generation,
            "parent_ids": [g.id],
        }
    )


def propose_variant(g: AttackGenome, overrides: dict | None, generation: int) -> AttackGenome:
    """Critic-proposed sibling: same TTPs, different parameter regime."""
    regime = critic_regime_overrides(g)
    merged = {**regime, **(overrides or {})}
    child = clone_with_params(g, merged, generation)
    child.origin = "critic"
    child.id = f"{g.id}-v{generation}"
    child.name = f"{g.name} (critic variant)"
    return child


def critic_regime_overrides(g: AttackGenome) -> dict:
    """Parameter-regime shifts that broaden attack diversity for the Critic."""
    overrides: dict[str, Any] = {}
    p = g.params
    for key in ("window_min", "duration_h", "harvest_delay_h", "dormancy_days",
                "duration_days", "burst_spread_h"):
        if key in p and isinstance(p[key], (list, tuple)) and len(p[key]) == 2:
            lo, hi = float(p[key][0]), float(p[key][1])
            overrides[key] = (round(lo * 1.4, 1), round(hi * 2.0, 1))
    for key in ("amount_range", "base_amount", "cnp_amount"):
        if key in p and isinstance(p[key], (list, tuple)) and len(p[key]) == 2:
            lo, hi = float(p[key][0]), float(p[key][1])
            overrides[key] = (lo, round(hi * 0.55, 0))
    for key in ("transfers", "cnp_txns", "burst_txns", "stages"):
        if key in p and isinstance(p[key], (list, tuple)) and len(p[key]) == 2:
            lo, hi = int(p[key][0]), int(p[key][1])
            overrides[key] = (max(1, lo - 1), hi + 1)
        elif key in p and isinstance(p[key], (int, float)):
            overrides[key] = int(p[key]) + 1
    if "hop_chains" in p:
        overrides["hop_chains"] = int(p["hop_chains"]) + 1
    if "night_bias" in p:
        overrides["night_bias"] = max(0.0, float(p["night_bias"]) - 0.2)
    if "amount_jitter" in p:
        overrides["amount_jitter"] = max(0.08, float(p["amount_jitter"]) * 0.6)
    overrides["critic_regime"] = True
    return overrides
