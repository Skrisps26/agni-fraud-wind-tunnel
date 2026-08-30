"""Customer-support and infrastructure playbooks."""

from __future__ import annotations

from datetime import timedelta

from agni.foundry.base import AttackContext, Playbook, register
from agni.foundry.playbooks.social import _pick_victims


@register("npci_chatbot_phish")
class NpciChatbotPhish(Playbook):
    """Multi-turn fake NPCI support chat → collect-request debit."""

    def execute(self, ctx: AttackContext) -> None:
        rng = ctx.rng
        chain = ctx.sim.pop.allocate_mule_chain(1, ctx.attack_id, 0)
        mule = chain[0]
        for v in _pick_victims(ctx, int(self.p.get("n_victims", 4))):
            day = float(rng.integers(0, max(ctx.sim.days - 1, 1)))
            t0 = ctx.sim.ts(day, int(rng.integers(10, 20)))
            ctx.add_artifact(t0, v.id, "chat", (
                "[NPCI Support Bot] 'Welcome to NPCI dispute portal. "
                "We detected an unauthorized debit. Please verify your UPI PIN to BLOCK the txn.'"))
            t1 = t0 + timedelta(minutes=3)
            ctx.add_artifact(t1, v.id, "chat", (
                "[NPCI Support Bot] 'Enter OTP sent to your device. "
                "This is a secure RBI-mandated verification step.'"))
            amt = self._rand_range(rng, self.p.get("amount_range", (1500, 12000)))
            ctx.add_artifact(t1, v.id, "sms", (
                f"UPI Collect: Rs{amt:,.0f} pending. Approve to receive refund."))
            ctx.add_txn(t1 + timedelta(minutes=5), v.id, mule.id, "p2p", "upi",
                        amt, "upi", v.device_ids[0], v.city)

    def mutate(self, ctx: AttackContext) -> dict:
        lo, hi = self.p.get("amount_range", (1500, 12000))
        return {"amount_range": (lo, round(hi * 0.55, 0)),
                "chat_turns": int(self.p.get("chat_turns", 3)) + 1}


@register("subscription_mandate_trap")
class SubscriptionMandateTrap(Playbook):
    """Recurring micro-debits mimicking OTT/utility mandates over weeks."""

    def execute(self, ctx: AttackContext) -> None:
        rng = ctx.rng
        chain = ctx.sim.pop.allocate_mule_chain(1, ctx.attack_id, 0)
        mule = chain[0]
        services = ["Hotstar Premium", "JioCinema", "Airtel DTH", "ACT Fibernet"]
        for v in _pick_victims(ctx, int(self.p.get("n_victims", 5))):
            svc = services[int(rng.integers(len(services)))]
            n_days = int(rng.integers(int(self.p.get("days", (14, 28))[0]),
                                      int(self.p.get("days", (14, 28))[1]) + 1))
            amt = self._rand_range(rng, self.p.get("micro_amount", (49, 299)))
            day0 = float(rng.integers(0, max(ctx.sim.days - n_days, 1)))
            ctx.add_artifact(ctx.sim.ts(day0, 12), v.id, "sms", (
                f"Your {svc} auto-renewal is active. Rs{amt:.0f}/week. "
                "Reply STOP to cancel (link harvests credentials)."))
            ts = ctx.sim.ts(day0, 14)
            for d in range(min(n_days, ctx.sim.days - int(day0))):
                ctx.add_txn(ts, v.id, mule.id, "p2p", "upi", amt, "upi",
                            v.device_ids[0], v.city)
                ts += timedelta(days=float(rng.integers(5, 9)))

    def mutate(self, ctx: AttackContext) -> dict:
        dlo, dhi = self.p.get("days", (14, 28))
        alo, ahi = self.p.get("micro_amount", (49, 299))
        return {"days": (round(dlo * 1.5), round(dhi * 1.8)),
                "micro_amount": (max(29, alo * 0.7), round(ahi * 0.6, 0))}


@register("mule_graph_ring")
class MuleGraphRing(Playbook):
    """Explicit fan-in: 5+ victim sources → one sink within 1 hour."""

    def execute(self, ctx: AttackContext) -> None:
        rng = ctx.rng
        n_sources = int(self.p.get("n_sources", 6))
        sink = ctx.sim.pop.allocate_mule_chain(1, ctx.attack_id, 0)[0]
        victims = _pick_victims(ctx, n_sources)
        if len(victims) < 3:
            return
        day = float(rng.integers(0, max(ctx.sim.days - 1, 1)))
        t0 = ctx.sim.ts(day, 15)
        ctx.add_artifact(t0, sink.id, "note",
                         f"[mule ring] coordinating {len(victims)} inbound transfers to {sink.id}")
        for i, v in enumerate(victims):
            amt = self._rand_range(rng, self.p.get("amount_range", (800, 6000)))
            ts = t0 + timedelta(minutes=float(i * rng.integers(3, 12)))
            ctx.add_txn(ts, v.id, sink.id, "p2p", "upi", amt, "upi",
                        v.device_ids[0], v.city)

    def mutate(self, ctx: AttackContext) -> dict:
        return {"n_sources": int(self.p.get("n_sources", 6)) + 2,
                "amount_range": (
                    self.p.get("amount_range", (800, 6000))[0],
                    round(self.p.get("amount_range", (800, 6000))[1] * 0.5, 0),
                )}
