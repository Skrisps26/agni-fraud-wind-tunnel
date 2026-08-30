# Shadow-mode occupancy (CISO one-pager)

AGNI is a **lab wind tunnel**, not a drop-in for Mastercard Decision Intelligence.

## What a bank would do

1. Map AGNI feature columns to DI fields (amount, velocity windows, destination fan-in, device novelty, message text).
2. Score in **batch** first (minutes), then a 50ms online stub on the same feature vector.
3. Freeze Sentinel. Run Critic mutations in the tunnel for N generations. **Time-to-evade** at 0.5% FPR is the go/no-go metric.
4. Analysts accept/reject Critic mutations (policy). Kill switch + FPR tripwire abort shadow if legit FPR exceeds budget.
5. Nightly retrain **in the tunnel only**. Promote weights only after family-holdout AUC holds.

## Privacy

Synthetic identities. IEEE-CIS stays off the server (`calibration.json` is aggregates). Occupancy API accepts **scores + labels**, not raw PAN/VPA.

## What we do not claim

Live UPI microdata, issuer 3DS, production Mastercard rules, or proof on tomorrow’s traffic.
