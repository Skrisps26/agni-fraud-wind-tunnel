"""Attack Foundry framework (Pillar 2: Generate).

A Playbook compiles an AttackGenome into executable behavior against the digital
twin: it appends fraudulent txns to the ledger and emits artifacts (scam texts,
call transcripts, forged docs) used by the text head of the defender.

Design rule: every playbook runs fully offline via deterministic templates.
If Config.llm_enabled, subclasses MAY enrich artifact text through the LLM hook.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import numpy as np

if TYPE_CHECKING:
    from agni.genome.schema import AttackGenome
    from agni.twin.rails import Simulation


@dataclass
class AttackContext:
    sim: "Simulation"
    rng: np.random.Generator
    attack_id: str
    params: dict[str, Any]
    feedback: dict[str, float] = field(default_factory=dict)
    touched_accounts: list[str] = field(default_factory=list)

    # ---------------------------------------------------------------- helpers
    def add_txn(self, ts, src, dst, kind, rail, amount, channel,
                device_id, city, merchant_id=None) -> None:
        from agni.twin.rails import Txn
        self.sim.ledger.add_txn(Txn(
            self.sim.ledger.next_txn_id(), ts, src, dst, kind, rail,
            round(float(amount), 2), channel, device_id, city,
            merchant_id, True, self.attack_id))
        if src not in self.touched_accounts:
            self.touched_accounts.append(src)

    def add_artifact(self, ts, src, kind, text) -> None:
        from agni.twin.rails import Artifact
        self.sim.ledger.add_artifact(Artifact(
            self.sim.ledger.next_art_id(), ts, src, kind, text, 1, self.attack_id))

    def victim_history(self, victim_id: str):
        """Victim's legit transactions so far - used for personalization."""
        return [t for t in self.sim.ledger.txns
                if t.src == victim_id and not t.is_fraud]


REGISTRY: dict[str, type["Playbook"]] = {}


def register(name: str) -> Callable:
    def deco(cls):
        REGISTRY[name] = cls
        cls.playbook_name = name
        return cls
    return deco


class Playbook:
    """Base class. Subclasses implement execute() and optionally mutate()."""

    def __init__(self, genome: "AttackGenome"):
        self.genome = genome

    @property
    def p(self) -> dict[str, Any]:
        return self.genome.params

    # ------------------------------------------------------------------ hooks
    def execute(self, ctx: AttackContext) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def mutate(self, ctx: AttackContext) -> dict[str, Any]:
        """Return param overrides nudging the vector toward evasion."""
        det = float(ctx.feedback.get("det_rate", 0.0))
        blind = ctx.feedback.get("blind_spots", []) or []
        strength = 2.0 if det < 0.5 else (1.6 if det < 0.7 else 1.15)
        out: dict[str, Any] = {}
        for key, val in self.p.items():
            if isinstance(val, tuple) and len(val) == 2 and all(
                    isinstance(x, (int, float)) for x in val):
                lo, hi = val
                if key in ("amount_range", "base_amount", "cnp_amount"):
                    out[key] = (lo, round(hi * (0.5 if "vel" in blind else 0.7), 0))
                elif key in ("window_min", "duration_h", "harvest_delay_h",
                             "dormancy_days", "duration_days", "burst_spread_h"):
                    out[key] = (round(lo * strength, 1), round(hi * strength, 1))
                else:
                    out[key] = (round(lo * strength, 2), round(hi * strength, 2))
        if "vel_10m" in blind or "vel_1h" in blind or "vel_24h" in blind:
            out.setdefault("slow_velocity", True)
        if "dst_fan_in" in blind or "dst_fwd_rate_24h" in blind:
            out.setdefault("hop_chains", int(self.p.get("hop_chains", 2)) + 1)
        if "amt_z_user" in blind:
            for key in ("amount_range", "base_amount", "cnp_amount"):
                if key in self.p and isinstance(self.p[key], (list, tuple)):
                    lo, hi = self.p[key]
                    out[key] = (round(lo * 0.3, 0), round(hi * 0.4, 0))
        return out

    # ------------------------------------------------------------- utilities
    @staticmethod
    def _rand_range(rng: np.random.Generator, r: tuple[float, float]) -> float:
        lo, hi = float(min(r)), float(max(r))
        return float(rng.uniform(lo, hi))


def build_playbook(genome: "AttackGenome") -> Playbook:
    from agni.foundry import playbooks  # noqa: F401 - ensures registration
    cls = REGISTRY.get(genome.playbook)
    if cls is None:
        raise KeyError(f"unknown playbook '{genome.playbook}' for {genome.id}")
    return cls(genome)
