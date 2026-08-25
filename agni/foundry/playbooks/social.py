"""Social-engineering playbooks: voice-clone UPI, digital arrest, CFO BEC,
personalized smishing. All content is synthetic template output - no real
person's voice/likeness/data is ever cloned or used."""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from agni.foundry.base import AttackContext, Playbook, register

HOSPITALS = ["Apollo Care", "City General Hospital", "Sanjeevani Multispeciality",
             "Fortis Health", "Civil Hospital"]
REASONS = [
    "met with an accident near the highway", "collapsed at the gym",
    "was admitted after a bike accident", "fainted at work - low BP",
]
SCAM_DOMAINS = ["refund-pay.xyz", "upi-verif.top", "quickrefunds.site",
                "bank-alerts.online", "payverify.icu"]


def _pick_victims(ctx: AttackContext, k: int, rich: bool = False) -> list:
    pop = ctx.sim.pop
    pool = sorted(pop.consumers, key=lambda c: -c.avg_amount)[: max(k * 4, 40)] if rich \
        else pop.consumers
    out = []
    for _ in range(k * 6):
        c = pool[int(ctx.rng.integers(len(pool)))]
        if len(ctx.victim_history(c.id)) >= 4 and all(x.id != c.id for x in out):
            out.append(c)
        if len(out) >= k:
            break
    return out


@register("voice_relative_upi")
class VoiceRelativeUpi(Playbook):
    """Voice-cloned 'relative in emergency' -> rushed UPI transfers to a fresh mule."""

    def execute(self, ctx: AttackContext) -> None:
        rng, pop = ctx.rng, ctx.sim.pop
        chain = pop.allocate_mule_chain(1, ctx.attack_id, 0)
        mule = chain[0]
        hour = int(rng.choice([21, 22, 23, 2])) if rng.random() < float(
            self.p.get("night_bias", 0.6)) else pop.sample_hour(rng)
        day = float(rng.integers(0, max(ctx.sim.days - 1, 1)))
        t0 = ctx.sim.ts(day, hour)
        for v in _pick_victims(ctx, int(self.p.get("n_victims", 3))):
            rel = f"{rng.choice(['Bhaiya', 'Papa', 'Mummy', 'Didi'])}"
            hosp = HOSPITALS[int(rng.integers(len(HOSPITALS)))]
            reason = REASONS[int(rng.integers(len(REASONS)))]
            n = int(rng.integers(int(self.p["transfers"][0]), int(self.p["transfers"][1]) + 1))
            window_min = self._rand_range(rng, self.p["window_min"])
            ctx.add_artifact(t0, v.id, "call_transcript", (
                "[VOICE CALL - cloned voice of {rel}] "
                "\"Hello {name}, main {rel} bol raha hoon...\" CallerID unknown. "
                "Story: your son {reason}; admitted at {hosp}, ICU deposit needed NOW. "
                "Caller pleads, background ambulance noise (AI-generated). "
                "Victim agrees to transfer immediately.").format(
                rel=rel, name=v.name.split()[0], reason=reason, hosp=hosp))
            ts = t0
            for i in range(n):
                amt = self._rand_range(rng, self.p["amount_range"])
                ts = ts + timedelta(minutes=window_min / max(n, 1))
                ctx.add_txn(ts, v.id, mule.id, "p2p", "upi", amt, "upi",
                            v.device_ids[0], v.city)

    def mutate(self, ctx: AttackContext) -> dict:
        det = float(ctx.feedback.get("det_rate", 0.0))
        s = 1.8 if det >= 0.5 else 1.25
        lo, hi = self.p["window_min"]
        alo, ahi = self.p["amount_range"]
        nb = max(0.0, float(self.p.get("night_bias", 0.6)) - 0.25)
        return {"window_min": (round(lo * s, 1), round(hi * s, 1)),
                "amount_range": (round(max(alo * 0.85, 500), 0), round(ahi * 0.55, 0)),
                "night_bias": round(nb, 2),
                "transfers": (int(self.p["transfers"][0]) + 1,
                              int(self.p["transfers"][1]) + 2)}


@register("digital_arrest")
class DigitalArrest(Playbook):
    """Deepfake video-call 'police/RBI' coercion draining savings over hours/days."""

    def execute(self, ctx: AttackContext) -> None:
        rng = ctx.rng
        chain = ctx.sim.pop.allocate_mule_chain(2, ctx.attack_id, 0)
        l1, l2 = chain
        fir = f"FIR/{rng.integers(100, 999)}/{rng.integers(2024, 2027)}"
        day = float(rng.integers(0, max(ctx.sim.days - 2, 1)))
        h0 = int(rng.integers(9, 19))
        dur_lo, dur_hi = self.p["duration_h"]
        duration_h = self._rand_range(rng, (float(dur_lo), float(dur_hi)))
        esc = float(self.p.get("escalation", 2.2))
        stages = int(self.p.get("stages", 3))
        for v in _pick_victims(ctx, int(self.p.get("n_victims", 2))):
            base = self._rand_range(rng, self.p["base_amount"]) * max(v.avg_amount / 350, 1)
            ctx.add_artifact(ctx.sim.ts(day, h0), v.id, "call_transcript", (
                "[VIDEO CALL] \"Officer Sharma, Cyber Crime Unit.\" Deepfake official badge overlay. "
                "\"Your Aadhaar is linked to money-laundering case {fir}. You are under digital arrest - "
                "do NOT disconnect the call.\" Background: AI-generated police station. "
                "Script pushes 'account verification' transfers to a 'safe RBI account'.").format(fir=fir))
            ts = ctx.sim.ts(day, h0)
            amt = base
            for s_i in range(stages):
                ctx.add_artifact(ts, v.id, "note",
                                 f"[stage {s_i + 1}/{stages}] 'verification tranche' Rs{amt:,.0f} demanded")
                ctx.add_txn(ts, v.id, l1.id, "p2p", "upi", amt, "imps",
                            v.device_ids[0], v.city)
                if rng.random() < 0.5:  # decoy: tiny 'RBI fee'
                    ctx.add_txn(ts, v.id, l1.id, "p2p", "upi", 11.0, "upi",
                                v.device_ids[0], v.city)
                amt *= esc
                ts = ts + timedelta(hours=duration_h / stages)
            # onward layering
            ctx.add_txn(ts, l1.id, l2.id, "p2p", "wire", amt / esc * 2.5, "neft",
                        f"d-agent-{ctx.attack_id}", "Mumbai")

    def mutate(self, ctx: AttackContext) -> dict:
        dur_lo, dur_hi = self.p["duration_h"]
        blo, bhi = self.p["base_amount"]
        return {"duration_h": (dur_lo, round(dur_hi * 1.5, 1)),
                "escalation": round(float(self.p.get("escalation", 2.2)) ** 0.85, 3),
                "stages": int(self.p.get("stages", 3)) + 1,
                "decoy_transfers": True,
                "base_amount": (blo, round(bhi * 0.6, 0))}


@register("cfo_bec_wire")
class CfoBecWire(Playbook):
    """LLM-drafted invoice thread with swapped beneficiary -> large RTGS wire."""

    def execute(self, ctx: AttackContext) -> None:
        rng = ctx.rng
        chain = ctx.sim.pop.allocate_mule_chain(1, ctx.attack_id, 0)
        mule = chain[0]
        hour = int(self.p.get("hour", 16))
        splits = int(self.p.get("split_max", 1))
        for v in _pick_victims(ctx, int(self.p.get("n_attacks", 2)), rich=True):
            total = self._rand_range(rng, self.p["amount_range"])
            day = float(rng.integers(0, max(ctx.sim.days - 1, 1)))
            iban = f"XXXX{rng.integers(10**8, 10**9 - 1)}"
            ctx.add_artifact(ctx.sim.ts(day, max(hour - 3, 0)), v.id, "email", (
                "Thread (LLM-generated, mirrors vendor tone): Re: PO-{po} final settlement. "
                "'Note our bank has changed - updated beneficiary A/c {iban} ({bank}).' "
                "Urgency cue: 'release today to avoid late penalty'. Signature block cloned "
                "from real vendor email footer.").format(po=rng.integers(10000, 99999),
                                                        iban=iban, bank=mule.bank_id))
            per = total / max(splits, 1)
            ts = ctx.sim.ts(day, hour)
            for i in range(splits):
                ctx.add_txn(ts, v.id, mule.id, "p2p", "wire", per, "rtgs",
                            v.device_ids[0], v.city)
                ts = ts + timedelta(minutes=int(rng.integers(20, 90)))

    def mutate(self, ctx: AttackContext) -> dict:
        lo, hi = self.p["amount_range"]
        return {"split_max": 3, "hour": 13,
                "amount_range": (lo, round(hi * 0.5, 0)),
                "reuse_vendor_thread": True}


@register("personalized_smishing")
class PersonalizedSmishing(Playbook):
    """LLM-phished SMS referencing the victim's REAL last purchase -> harvested
    card -> CNP spend at high-risk MCCs."""

    def execute(self, ctx: AttackContext) -> None:
        rng, pop = ctx.rng, ctx.sim.pop
        chain = pop.allocate_mule_chain(1, ctx.attack_id, 0)
        mule = chain[0]
        delay_lo, delay_hi = self.p.get("harvest_delay_h", (1, 4))
        cnf_lo, cnf_hi = self.p.get("cnp_txns", (3, 6))
        for v in _pick_victims(ctx, int(self.p.get("n_victims", 6))):
            merch = [t for t in ctx.victim_history(v.id) if t.kind == "p2m"]
            if not merch:
                continue
            last = merch[-1]
            m = pop.merchant_by_id.get(last.merchant_id)
            mname = m.name if m else "the store"
            dom = SCAM_DOMAINS[int(rng.integers(len(SCAM_DOMAINS)))]
            refund = round(float(last.amount) * 1.4, 2)
            t_sms = last.ts + timedelta(hours=self._rand_range(rng, (float(delay_lo), float(delay_hi))))
            ctx.add_artifact(t_sms, v.id, "sms", (
                "Dear {name}, Rs{amt} was WRONGLY debited at {m} on {d}. Refund Rs{r} "
                "pending - confirm your {bank} details at https://{dom}/r?ref={n4} "
                "within 24h. - {bank} Desks").format(
                name=v.name.split()[0], amt=f"{last.amount:,.0f}", m=mname,
                d=last.ts.strftime("%d/%m"), r=f"{refund:,.0f}",
                bank=v.bank_id.split()[0], dom=dom, n4=f"{rng.integers(1000, 9999)}"))
            dev = f"d-harvest-{ctx.attack_id}-{v.id}"
            n_cnp = int(rng.integers(int(cnf_lo), int(cnf_hi) + 1))
            ts = t_sms + timedelta(hours=float(delay_hi))
            for _ in range(n_cnp):
                target = pop.sample_merchant(rng, high_risk=True)
                amt = self._rand_range(rng, self.p.get("cnp_amount", (800, 9000)))
                ctx.add_artifact(ts, v.id, "note",
                                 f"[harvested-card CNP] {target.name} Rs{amt:,.0f}")
                ctx.add_txn(ts, v.id, target.id, "p2m", "card", amt, "online",
                            dev, v.city, target.id)
                ts = ts + timedelta(minutes=float(rng.integers(8, 240)))
            ctx.add_txn(ts, v.id, mule.id, "p2p", "wallet",
                        self._rand_range(rng, (1500, 12000)), "imps", dev, v.city)

    def mutate(self, ctx: AttackContext) -> dict:
        dlo, dhi = self.p.get("harvest_delay_h", (1, 4))
        clo, chi = self.p.get("cnp_txns", (3, 6))
        alo, ahi = self.p.get("cnp_amount", (800, 9000))
        return {"harvest_delay_h": (dlo, round(dhi * 3, 1)),
                "cnp_txns": (max(2, clo), chi),
                "cnp_amount": (alo, round(ahi * 0.45, 0)),
                "mimic_recent_merchants": True}
