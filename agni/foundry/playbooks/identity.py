"""Identity & behavior playbooks: GenAI synthetic-KYC bust-out and
behavioral-mimicry stealth drain."""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from agni.foundry.base import AttackContext, Playbook, register
from agni.foundry.playbooks.social import _pick_victims


@register("synthetic_kyc")
class SyntheticKycBustout(Playbook):
    """AI-forged documents + deepfake liveness pass onboarding; account sleeps,
    then busts out through high-risk spend and cash-out."""

    def execute(self, ctx: AttackContext) -> None:
        rng = ctx.rng
        chain = ctx.sim.pop.allocate_mule_chain(1, ctx.attack_id, 0)
        mule = chain[0]
        dorm_lo, dorm_hi = self.p.get("dormancy_days", (8, 18))
        burst = int(self.p.get("burst_txns", 8))
        spread_h = float(self.p.get("burst_spread_h", 6))
        for _ in range(int(self.p.get("n_identities", 2))):
            name = f"{rng.choice(['Rahul', 'Sneha', 'Imran', 'Meera'])} {rng.choice(['Kulkarni', 'Chawla', 'Fernandes'])}"
            pan = f"{chr(65 + rng.integers(26))}{chr(65 + rng.integers(26))}XPS{rng.integers(1000, 9999)}{chr(65 + rng.integers(26))}"
            day0 = float(rng.integers(0, max(ctx.sim.days - int(dorm_hi) - 1, 1)))
            dev = f"d-syn-{ctx.attack_id}-{int(rng.integers(1000, 9999))}"
            t0 = ctx.sim.ts(day0, int(rng.integers(10, 18)))
            ctx.add_artifact(t0, f"SYN-{pan}", "doc", (
                "KYC packet: PAN {pan}, name {name}, DOB {dob}, addr Bengaluru. "
                "ID photo: GAN-generated face (no database hit). Selfie-video liveness: "
                "deepfake render passes blink/turn checks. Address proof: AI-edited utility bill."
                ).format(pan=pan, name=name,
                         dob=f"{rng.integers(1975, 2003)}-{rng.integers(1, 13):02d}-{rng.integers(1, 28):02d}"))
            ctx.add_artifact(t0, f"SYN-{pan}", "onboarding",
                             f"[onboarded] wallet + savings a/c opened for {name}; device {dev}")
            syn = f"SYN-{pan}"
            t1 = t0 + timedelta(days=self._rand_range(rng, (float(dorm_lo), float(dorm_hi))))
            # quiet 'warming' inflows to build limits credibility
            for i in range(max(burst // 4, 1)):
                ctx.add_txn(t1, syn, mule.id, "p2p", "upi",
                            self._rand_range(rng, (3000, 15000)), "imps", dev, "Bengaluru")
                t1 += timedelta(hours=spread_h / 4)
            # bust-out burst at high-risk merchants + cash-out
            ts = t1
            hi = [m for m in ctx.sim.pop.merchants if m.is_high_risk]
            for i in range(burst):
                target = hi[int(rng.integers(len(hi)))]
                amt = round(float(rng.lognormal(np.log(target.median_amount), target.sigma)), 2)
                ctx.add_txn(ts, syn, target.id, "p2m", "card", amt, "online",
                            dev, "Bengaluru", target.id)
                ts += timedelta(hours=spread_h / max(burst, 1))
            ctx.add_txn(ts, syn, mule.id, "p2p", "wallet",
                        self._rand_range(rng, (40000, 250000)), "imps", dev, "Bengaluru")

    def mutate(self, ctx: AttackContext) -> dict:
        dlo, dhi = self.p.get("dormancy_days", (8, 18))
        return {"dormancy_days": (round(dlo * 1.6, 1), round(dhi * 1.9, 1)),
                "burst_txns": int(self.p.get("burst_txns", 8)) + 4,
                "burst_spread_h": 72.0,
                "warmup_inflows": True}


@register("behavioral_mimicry")
class BehavioralMimicryDrain(Playbook):
    """Stolen credentials replaying the victim's own category/hour profile -
    small amounts, long horizon - to hide inside the baseline."""

    def execute(self, ctx: AttackContext) -> None:
        rng = ctx.rng
        chain = ctx.sim.pop.allocate_mule_chain(1, ctx.attack_id, 0)
        mule = chain[0]
        jit = float(self.p.get("amount_jitter", 0.35))
        d_lo, d_hi = self.p.get("duration_days", (4, 8))
        tp_lo, tp_hi = self.p.get("txns_per_day", (2, 4))
        for v in _pick_victims(ctx, int(self.p.get("n_victims", 3))):
            hist = [t for t in ctx.victim_history(v.id) if t.kind == "p2m"]
            if len(hist) < 4:
                continue
            cat_medians: dict[str, list[float]] = {}
            hours: list[int] = []
            for t in hist:
                m = ctx.sim.pop.merchant_by_id.get(t.merchant_id)
                key = m.category if m else "grocery"
                cat_medians.setdefault(key, []).append(t.amount)
                hours.append(t.ts.hour)
            start_day = float(max((hist[-1].ts - ctx.sim.start).days, 0)) + 0.2
            cats = list(cat_medians)
            weights = np.array([len(v_) for v_ in cat_medians.values()], dtype=float)
            weights /= weights.sum()
            dur = self._rand_range(rng, (float(d_lo), float(d_hi)))
            n_days = min(int(np.ceil(dur)), max(ctx.sim.days - int(start_day), 1))
            dev = v.device_ids[int(rng.integers(len(v.device_ids)))]
            ctx.add_artifact(ctx.sim.start + timedelta(days=start_day),
                             v.id, "note",
                             f"[credential abuse] card-not-present kit active on device {dev}; "
                             "spend profile cloned from victim history")
            for d_i in range(n_days):
                for _ in range(int(rng.integers(int(tp_lo), int(tp_hi)) + 1)):
                    cat = cats[int(rng.choice(len(cats), p=weights))]
                    base_amt = float(np.median(cat_medians[cat]))
                    amt = base_amt * (1 + rng.normal(0, jit))
                    hour = int(hours[int(rng.integers(len(hours)))])
                    ts = ctx.sim.ts(start_day + d_i, hour, int(rng.integers(60)))
                    target = ctx.sim.pop.sample_merchant(rng)
                    ctx.add_txn(ts, v.id, target.id, "p2m", "card",
                                max(round(float(amt), 2), 40.0), "online",
                                dev, v.city, target.id)
            # periodic siphon of accumulated balance
            ts_end = ctx.sim.ts(min(start_day + n_days, ctx.sim.days - 0.05),
                                int(rng.integers(1, 5)))
            ctx.add_txn(ts_end, v.id, mule.id, "p2p", "wallet",
                        self._rand_range(rng, (900, 7000)), "upi", dev, v.city)

    def mutate(self, ctx: AttackContext) -> dict:
        d_lo, d_hi = self.p.get("duration_days", (4, 8))
        return {"amount_jitter": 0.15,
                "duration_days": (d_lo, round(d_hi * 1.7, 1)),
                "txns_per_day": (1, 2),
                "siphon_interval_days": 3}
