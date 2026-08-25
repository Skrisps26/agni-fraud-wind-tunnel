# Real-data anchor

AGNI's digital twin is calibrated against a **real, public transaction dataset**
so that fidelity claims are measured, not asserted.

## Setup (one-time)

1. Create a free Kaggle account and accept the competition rules at
   <https://www.kaggle.com/c/ieee-fraud-detection> (required by the data license).
2. Download `train_transaction.csv` into this directory:

   ```
   data/anchor/train_transaction.csv
   ```

   Either via the website or `kaggle competitions download -c ieee-fraud-detection -f train_transaction.csv`.
3. Fit the twin to it:

   ```bash
   make calibrate          # python -m agni.twin.calibrate
   ```

This writes `agni/twin/calibration.json` (committed: derived statistics only,
no raw rows). The Red Queen loop auto-detects it:

- Population ticket sizes and hour-of-day shape come from the fitted params.
- The Fidelity Judge scores attacks with KS distance against the **real**
  amount/hour marginals instead of the twin's own traffic.

## What we take from the anchor

| Signal | Use |
|---|---|
| `TransactionAmt` log-normal fit | consumer ticket-size level (USD -> INR via `AGNI_USD_INR`) |
| `TransactionDT` hour-of-day shape | circadian activity profile |
| per-`ProductCD` medians | reference for category price points |

## License note

IEEE-CIS/Vesta data is for competition/research use; raw CSVs must not be
redistributed (gitignored here). Only derived aggregate statistics
(`calibration.json`, paper figures) are committed.
