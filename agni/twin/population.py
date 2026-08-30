"""Digital-twin population: consumers, merchants, devices, banks, mule accounts.

Distributions are calibrated to look like real Indian retail payments:
log-normal ticket sizes per merchant category, circadian activity profiles,
payday concentration, urban geography. Everything is synthetic - no real PII.

When agni/twin/calibration.json exists (fitted from a real public anchor
dataset - see twin/calibrate.py), ticket-size level and hour-of-day shape come
from those fitted parameters instead of the hardcoded defaults.
"""

from __future__ import annotations

import numpy as np

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Ishaan", "Kabir", "Rohan", "Arjun", "Rahul",
    "Neha", "Ananya", "Priya", "Diya", "Meera", "Kavya", "Pooja", "Sneha",
    "Rajesh", "Suresh", "Vikram", "Amit", "Sanjay", "Deepak", "Manish",
    "Lakshmi", "Sunita", "Rekha", "Aarti", "Farhan", "Imran", "Zoya",
]
LAST_NAMES = [
    "Sharma", "Patel", "Reddy", "Nair", "Iyer", "Gupta", "Verma", "Joshi",
    "Mehta", "Desai", "Kulkarni", "Rao", "Menon", "Chopra", "Bose", "Das",
    "Malhotra", "Kapoor", "Shetty", "Pillai", "Agarwal", "Mishra", "Singh",
]
CITIES = [
    ("Mumbai", 0.13), ("Delhi", 0.11), ("Bengaluru", 0.11), ("Hyderabad", 0.08),
    ("Pune", 0.07), ("Ahmedabad", 0.06), ("Chennai", 0.06), ("Kolkata", 0.06),
    ("Jaipur", 0.05), ("Lucknow", 0.04), ("Indore", 0.04), ("Kochi", 0.04),
    ("Surat", 0.04), ("Nagpur", 0.03), ("Bhopal", 0.03), ("Patna", 0.03),
    ("Guwahati", 0.02),
]
# category -> (median INR, lognormal sigma, popularity weight)
CATEGORIES = {
    "grocery":          (420,   0.55, 0.20),
    "food_delivery":    (540,   0.45, 0.12),
    "fuel":             (950,   0.35, 0.09),
    "transport":        (180,   0.60, 0.10),
    "utilities":        (1400,  0.50, 0.06),
    "mobile_recharge":  (300,   0.50, 0.09),
    "pharmacy":         (640,   0.60, 0.05),
    "apparel":          (1900,  0.70, 0.07),
    "electronics":      (8200,  0.85, 0.05),
    "travel":           (6500,  0.90, 0.04),
    "entertainment":    (450,   0.55, 0.05),
    "jewelry":          (26000, 0.95, 0.02),
    "education":        (5200,  0.80, 0.03),
}
HIGH_RISK_CATEGORIES = {
    "gift_cards":         (2800, 0.80, 0.010),
    "crypto_exchange":    (9500, 0.90, 0.006),
    "electronics_resale": (6800, 0.75, 0.007),
    "betting_offshore":   (3600, 0.85, 0.004),
}
MERCHANT_SUFFIX = ["Mart", "Store", "Traders", "Bazaar", "Point", "Hub", "Zone", "World"]
BRAND_STEMS = ["Fresh", "Quick", "Urban", "Metro", "Sunrise", "GreenLeaf", "Prime",
               "ValuePlus", "CityCart", "Daily", "SmartBuy", "Neo", "Apex", "Omni"]

BANKS = [
    ("Bharat Bank", "@bharat"), ("NovaPay Bank", "@novapay"),
    ("Saral Finance", "@saral"), ("Indus One", "@indus1"),
    ("Deccan Commercial", "@deccan"), ("Meridian Pay", "@meridian"),
    ("Kaveri Co-op", "@kaveri"), ("Trimurti SB", "@trimurti"),
]
OS_CHOICES = ["android-14", "android-15", "ios-18", "ios-17"]

HOUR_WEIGHTS = np.array([
    0.15, 0.10, 0.06, 0.04, 0.03, 0.04, 0.08, 0.18,
    0.45, 0.85, 1.30, 1.60, 1.45, 1.20, 1.10, 1.25,
    1.50, 1.70, 1.80, 1.65, 1.35, 0.95, 0.60, 0.30,
])
HOUR_WEIGHTS = HOUR_WEIGHTS / HOUR_WEIGHTS.sum()


class Consumer:
    __slots__ = ("id", "name", "city", "bank_id", "upi_handle", "device_ids",
                 "avg_amount", "amount_sigma", "tenure_days", "evening_bias")

    def __init__(self, cid, name, city, bank_id, upi_handle, device_ids,
                 avg_amount, amount_sigma, tenure_days, evening_bias):
        self.id = cid; self.name = name; self.city = city
        self.bank_id = bank_id; self.upi_handle = upi_handle
        self.device_ids = device_ids; self.avg_amount = avg_amount
        self.amount_sigma = amount_sigma; self.tenure_days = tenure_days
        self.evening_bias = evening_bias


class Merchant:
    __slots__ = ("id", "name", "category", "city", "median_amount",
                 "sigma", "is_high_risk")

    def __init__(self, mid, name, category, city, median_amount, sigma, is_high_risk):
        self.id = mid; self.name = name; self.category = category; self.city = city
        self.median_amount = median_amount; self.sigma = sigma
        self.is_high_risk = is_high_risk


class Mule:
    """Disposably allocated mule account for attacker chains."""
    __slots__ = ("id", "bank_id", "tag", "opened_day")

    def __init__(self, mid, bank_id, tag, opened_day):
        self.id = mid; self.bank_id = bank_id; self.tag = tag; self.opened_day = opened_day


class Population:
    def __init__(self, consumers, merchants, devices, mules, hour_weights=None):
        self.consumers: list[Consumer] = consumers
        self.merchants: list[Merchant] = merchants
        self._merchant_p = None
        self.devices: list[str] = devices
        self.mules: list[Mule] = mules
        self.consumer_by_id = {c.id: c for c in consumers}
        self.merchant_by_id = {m.id: m for m in merchants}
        self._mule_cursor = {}
        hw = np.asarray(hour_weights, dtype=float) \
            if hour_weights is not None else HOUR_WEIGHTS
        self.hour_weights = hw / hw.sum()

    # ------------------------------------------------------------------ build
    @classmethod
    def generate(cls, n_consumers: int, n_merchants: int,
                 rng: np.random.Generator,
                 calibration: dict | None = None) -> "Population":
        cities_, w = zip(*CITIES)
        w = np.asarray(w) / sum(w)

        merchants: list[Merchant] = []
        cat_items = list(CATEGORIES.items())
        hi_items = list(HIGH_RISK_CATEGORIES.items())
        cat_names, cat_stats = zip(*cat_items)
        cat_w = np.array([s[2] for s in cat_stats]); cat_w /= cat_w.sum()
        hi_names, hi_stats = zip(*hi_items)
        hi_w = np.array([s[2] for s in hi_stats]); hi_w /= hi_w.sum()
        # Zipf-like merchant popularity for a sparse UPI P2M graph.
        merch_rank = np.arange(1, n_merchants + 1)
        merch_zipf = 1.0 / np.power(merch_rank, 0.85)
        merch_zipf /= merch_zipf.sum()
        for i in range(n_merchants):
            if i < int(0.94 * n_merchants):
                ci = rng.choice(len(cat_names), p=cat_w)
                cat = cat_names[ci]; med, sig, _ = cat_stats[ci]; hr = False
            else:
                ci = rng.choice(len(hi_names), p=hi_w)
                cat = hi_names[ci]; med, sig, _ = hi_stats[ci]; hr = True
            name = f"{rng.choice(BRAND_STEMS)} {rng.choice(MERCHANT_SUFFIX)}"
            merchants.append(Merchant(f"m{i:04d}", name, str(cat),
                                      str(rng.choice(cities_, p=w)),
                                      float(med), float(sig), hr))

        consumers: list[Consumer] = []
        devices: list[str] = []
        for i in range(n_consumers):
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            city = str(rng.choice(cities_, p=w))
            bank_id, handle = BANKS[rng.integers(len(BANKS))]
            d1 = f"d{i:05d}a"
            devices.append(d1)
            devs = [d1]
            if rng.random() < 0.35:
                d2 = f"d{i:05d}b"; devices.append(d2); devs.append(d2)
            # per-consumer baseline ticket size: lognormal around 350 INR
            avg = float(np.exp(np.log(350) + rng.normal(0, 0.7)))
            consumers.append(Consumer(
                f"c{i:05d}", name, city, bank_id,
                f"{name.split()[0].lower()}{rng.integers(100, 9999)}{handle}",
                devs, avg, float(rng.uniform(0.5, 0.9)),
                int(rng.integers(120, 3200)), float(rng.random()),
            ))

        mules = [Mule(f"mu{i:04d}", BANKS[rng.integers(len(BANKS))][0], "", -1)
                 for i in range(64)]

        pop = cls(consumers, merchants, devices, mules)
        pop._merchant_p = merch_zipf

        # ---- real-anchor calibration -------------------------------------
        if calibration:
            target = calibration.get("consumer_median_inr")
            if target:
                cur = float(np.median([c.avg_amount for c in consumers]))
                if cur > 0:
                    f = float(target) / cur
                    for c in consumers:
                        c.avg_amount = round(c.avg_amount * f, 2)
            hw = calibration.get("hour_weights")
            if hw and len(hw) == 24:
                arr = np.asarray(hw, dtype=float)
                pop.hour_weights = arr / arr.sum()
        return pop

    # ------------------------------------------------------------------ helpers
    def allocate_mule_chain(self, length: int, tag: str, day: int) -> list[Mule]:
        start = self._mule_cursor.get(tag, 0)
        chain = [self.mules[(start + k) % len(self.mules)] for k in range(length)]
        for m in chain:
            m.tag = tag
            if m.opened_day < 0:
                m.opened_day = day
        self._mule_cursor[tag] = (start + max(length, 1)) % len(self.mules)
        return chain

    def sample_hour(self, rng: np.random.Generator, consumer: Consumer | None = None) -> int:
        if consumer is not None and rng.random() < 0.35:
            shift = int(consumer.evening_bias * 3)
            hw = np.roll(self.hour_weights, shift)
            return int(rng.choice(24, p=hw))
        return int(rng.choice(24, p=self.hour_weights))

    def sample_merchant(self, rng: np.random.Generator, high_risk: bool | None = None) -> Merchant:
        pool = ([m for m in self.merchants if m.is_high_risk] if high_risk
                else [m for m in self.merchants if not m.is_high_risk] if high_risk is not None
                else self.merchants)
        if high_risk is None and self._merchant_p is not None and len(self._merchant_p) == len(self.merchants):
            return self.merchants[int(rng.choice(len(self.merchants), p=self._merchant_p))]
        return pool[int(rng.integers(len(pool)))]

    def merchant_txn_amount(self, rng: np.random.Generator, m: Merchant) -> float:
        return round(float(rng.lognormal(np.log(m.median_amount), m.sigma)), 2)

    def p2p_amount(self, rng: np.random.Generator, c: Consumer) -> float:
        return round(float(rng.lognormal(np.log(max(c.avg_amount * 0.8, 40)),
                                         c.amount_sigma)), 2)
