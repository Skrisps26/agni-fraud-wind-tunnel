"""Rails: transaction ledger, message/document artifacts, background traffic.

The Simulation owns the clock and produces legitimate traffic; Foundry playbooks
inject attacks into the same ledger so defenders see one unified stream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

START_DATE = datetime(2026, 8, 3)


@dataclass
class Txn:
    txn_id: str
    ts: datetime
    src: str
    dst: str
    kind: str            # p2m | p2p
    rail: str            # card | upi | wire | wallet
    amount: float
    channel: str         # pos | online | upi | neft | rtgs | imps | agent
    device_id: str
    city: str
    merchant_id: str | None
    is_fraud: bool
    attack_id: str = ""


@dataclass
class Artifact:
    art_id: str
    ts: datetime
    src: str             # account that sent/received the content
    kind: str            # sms | email | call_transcript | doc | listing | onboarding | note
    text: str
    label: int           # 1 = attack artifact, 0 = benign
    attack_id: str = ""
    forge_source: str = "template"  # template | llm


@dataclass
class Ledger:
    txns: list[Txn] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    _n = 0
    _na = 0

    def add_txn(self, t: Txn) -> None:
        self.txns.append(t)

    def add_artifact(self, a: Artifact) -> None:
        self.artifacts.append(a)

    def next_txn_id(self) -> str:
        self._n += 1
        return f"t{self._n:07d}"

    def next_art_id(self) -> str:
        self._na += 1
        return f"a{self._na:06d}"

    def to_df(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "txn_id": t.txn_id, "ts": t.ts, "src": t.src, "dst": t.dst,
            "kind": t.kind, "rail": t.rail, "amount": t.amount,
            "channel": t.channel, "device_id": t.device_id, "city": t.city,
            "merchant_id": t.merchant_id, "is_fraud": int(t.is_fraud),
            "attack_id": t.attack_id,
        } for t in self.txns])

    def artifacts_df(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "art_id": a.art_id, "ts": a.ts, "src": a.src, "kind": a.kind,
            "text": a.text, "label": a.label, "attack_id": a.attack_id,
            "forge_source": a.forge_source,
        } for a in self.artifacts])


BENIGN_SMS = [
    "Your OTP for {bank} net banking login is {otp}. Valid 10 min. Do not share with anyone.",
    "{bank}: Rs{amt} debited from A/c XX{n4} on {date} for UPI payment to {merchant}. Not you? Call 1800-XXX.",
    "{bank}: Rs{amt} credited to A/c XX{n4}. Bal Rs{bal}. -{bank}",
    "Your {item} order has been dispatched and will arrive by {date}. Track: trk.ly/{n6}",
    "Payment of Rs{amt} to {merchant} completed via UPI. Ref no {n9}.",
    "Reminder: your {bank} credit card bill of Rs{amt} is due on {date}.",
]


class Simulation:
    def __init__(self, population, days: int, start: datetime | None = None,
                 daily_lambda: float = 1.15, benign_msg_cap: int = 2500):
        self.pop = population
        self.days = days
        self.start = start or START_DATE
        self.end = self.start + timedelta(days=days)
        self.ledger = Ledger()
        self.daily_lambda = daily_lambda
        self.benign_msg_cap = benign_msg_cap

    # ------------------------------------------------------------------ clock
    def ts(self, day_offset: float, hour: int, minute: int = 0) -> datetime:
        base = self.start + timedelta(days=float(day_offset))
        return base.replace(hour=int(hour) % 24, minute=int(minute) % 60)

    def random_ts(self, rng: np.random.Generator, day_lo: float = 0.0,
                  day_hi: float | None = None) -> datetime:
        day_hi = self.days if day_hi is None else day_hi
        d = rng.uniform(day_lo, max(day_hi - 0.01, day_lo + 0.01))
        hour = self.pop.sample_hour(rng)
        return self.start + timedelta(days=float(d), hours=float(hour),
                                      minutes=float(rng.integers(0, 60)))

    # ---------------------------------------------------------- legit traffic
    def background_traffic(self, rng: np.random.Generator) -> int:
        """Generate legitimate consumer activity across the horizon."""
        pop = self.pop
        lam = self.days * self.daily_lambda
        n_added = 0
        for c in pop.consumers:
            count = rng.poisson(lam * 0.35 + 4)
            count = min(count, self.days * 4)
            for _ in range(count):
                ts = self.random_ts(rng)
                dev = c.device_ids[int(rng.integers(len(c.device_ids)))]
                if rng.random() < 0.72:
                    m = pop.sample_merchant(rng)
                    amt = pop.merchant_txn_amount(rng, m)
                    rail = "card" if rng.random() < 0.3 else "upi"
                    if rail == "card":
                        ch = "pos" if rng.random() < 0.7 else "online"
                    else:
                        ch = "upi_collect" if rng.random() < 0.12 else "upi_pay"
                    self.ledger.add_txn(Txn(
                        self.ledger.next_txn_id(), ts, c.id, m.id, "p2m", rail,
                        amt, ch, dev, c.city, m.id, False))
                else:
                    peer = pop.consumers[int(rng.integers(len(pop.consumers)))]
                    while peer.id == c.id:
                        peer = pop.consumers[int(rng.integers(len(pop.consumers)))]
                    self.ledger.add_txn(Txn(
                        self.ledger.next_txn_id(), ts, c.id, peer.id, "p2p", "upi",
                        pop.p2p_amount(rng, c), "upi_pay", dev, c.city, None, False))
                n_added += 1
        # benign message artifacts (capped sample keeps text head balanced/fast)
        cap = min(len(pop.consumers), self.benign_msg_cap)
        idx = rng.choice(len(pop.consumers), size=min(cap, 2200), replace=False)
        for i in idx:
            c = pop.consumers[i]
            tmpl = BENIGN_SMS[int(rng.integers(len(BENIGN_SMS)))]
            text = tmpl.format(
                bank=c.bank_id.split()[0], otp=f"{rng.integers(100000, 999999)}",
                amt=rng.integers(120, 9000), n4=f"{rng.integers(1000, 9999)}",
                date=(self.start + timedelta(days=int(rng.integers(self.days)))).strftime("%d-%m-%y"),
                merchant=pop.sample_merchant(rng).name, bal=rng.integers(500, 90000),
                item=rng.choice(["Flipkart", "Zomato", "Amazon", "IRCTC"]),
                n6=f"{rng.integers(100000, 999999)}", n9=f"{rng.integers(10**8, 10**9 - 1)}")
            self.ledger.add_artifact(Artifact(
                self.ledger.next_art_id(), self.random_ts(rng), c.id, "sms",
                text, 0))
        return n_added
