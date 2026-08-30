# AGNI — Mastercard Innovation Challenge 2026 Submission

## Deliverables

| Artifact | Location |
|----------|----------|
| Code repository | This repo |
| Solution walkthrough (.docx) | [`docs/AGNI_Solution_Walkthrough.docx`](docs/AGNI_Solution_Walkthrough.docx) |
| Working web prototype | `make api` → http://localhost:8000 |

## Architecture

```
Identify (Fraud Genome) → Generate (Foundry + Twin + Judge) → Defend (Sentinel)
         ↑                                                          |
         └──────────── Critic + feature-aware mutation ←─────────────┘
```

## Evaluation Results (multi-seed)

| Metric | Mean (seeds 7, 42, 99) |
|--------|--------------------------|
| ROC AUC | 0.9966 ± 0.0009 |
| Recall | 92.2% ± 1.4% |
| FPR | 0.41% ± 0.07% |
| Precision | 97.7% |
| Fidelity vs anchor | 0.623 |
| Time-to-Evade | 4 generations |
| Attack vectors | 35 (+ critic variants at runtime) |

Full per-seed data: [`runs/benchmarks.json`](runs/benchmarks.json)

## Three Pillars

### 1. Identify — 35 Fraud Genome vectors
Machine-readable JSON schema covering UPI, card, wire, wallet rails; social engineering, KYC, agentic checkout, behavioral, customer support, and infrastructure surfaces.

### 2. Generate — 10 playbooks, fidelity-judged
Digital twin calibrated on IEEE-CIS marginals. Fidelity Judge scores KS similarity against real anchor data.

### 3. Defend — Sentinel fusion detector
HistGradientBoosting + TF-IDF text head. FPR-budgeted threshold (≤0.5%). SHAP-lite analyst explanations.

## Reproduction

```bash
make setup
make calibrate   # optional: place IEEE-CIS train_transaction.csv in data/anchor/
make loop        # 5 Red Queen generations
make api         # dashboard at :8000
make test
```

## Demo Script (GFF)

1. Open dashboard → Genome Browser → filter `upi` → GEN-002 digital arrest
2. Press **Run generation** → watch frozen-defender AUC chart
3. Attack Theater → walk kill-chain artifact + flagged txn
4. Defense Console → SHAP-lite on top alert → cite TtE badge

## Responsible Use

Sandbox simulation only. Synthetic identities. TTP-level playbooks for detection research — not operational scam tooling.
