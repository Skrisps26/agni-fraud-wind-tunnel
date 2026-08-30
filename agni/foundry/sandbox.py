"""Scout-compiled playbooks: sandbox-register a Foundry class or record a hole.

Codegen is restricted: the class must subclass Playbook and call add_txn/add_artifact
only. If compile fails, Identify records an executable=False genome (documented hole).
"""

from __future__ import annotations

from datetime import timedelta

from agni.foundry.base import AttackContext, Playbook, REGISTRY, register
from agni.foundry.playbooks.social import _pick_victims


def compile_or_bind(generation: int, hole: dict | None,
                    genomes: list) -> tuple[str, str]:
    """Return (playbook_key, note). Prefer a new registered class; else bind existing."""
    key = f"scout_compiled_{generation}"
    if key in REGISTRY:
        return key, "reused compiled playbook"

    @register(key)
    class ScoutCompiled(Playbook):
        """Slow UPI-collect drip compiled from an atlas hole (sandbox)."""

        def execute(self, ctx: AttackContext) -> None:
            rng = ctx.rng
            n = int(self.p.get("n_attacks", 3))
            chain = ctx.sim.pop.allocate_mule_chain(2, ctx.attack_id, 0)
            mule = chain[-1]
            for v in _pick_victims(ctx, n):
                day = float(rng.integers(0, max(ctx.sim.days - 1, 1)))
                hole_note = (hole or {}).get("note", "Scout-compiled collect drip")
                rail = (hole or {}).get("rail", "upi")
                ctx.add_chain(v.id, day, [
                    ("call_transcript",
                     f"[synthetic] Scout compile ({rail}): {hole_note}", 0),
                    ("sms",
                     "NPCI-style collect request (synthetic). Approve only if you initiated.",
                     int(rng.integers(8, 40))),
                ])
                t0 = ctx.sim.ts(day, int(rng.integers(10, 22)))
                amt = float(rng.uniform(400, 2400))
                ctx.add_txn(t0 + timedelta(minutes=45), v.id, mule.id,
                            "p2p", "upi", amt, "upi_collect",
                            v.device_ids[0], v.city)

        def mutate(self, ctx: AttackContext) -> dict:
            return {"n_attacks": max(1, int(self.p.get("n_attacks", 3)) - 1),
                    "slow_velocity": True}

    note = f"compiled {key} from hole={hole}" if hole else f"compiled {key}"
    return key, note
