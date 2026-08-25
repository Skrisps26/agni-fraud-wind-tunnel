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
    origin: Literal["seed", "critic"] = "seed"
    parent_ids: list[str] = Field(default_factory=list)
    generation_born: int = 0


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


def propose_variant(g: AttackGenome, overrides: dict, generation: int) -> AttackGenome:
    """Critic-proposed sibling: same TTPs, different parameter regime."""
    child = clone_with_params(g, overrides, generation)
    child.origin = "critic"
    child.id = f"{g.id}-v{generation}"
    child.name = f"{g.name} (critic variant)"
    return child
