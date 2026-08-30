# AGNI — Mastercard Innovation Challenge 2026

## Triple-Agent Fraud Wind Tunnel

| Agent | Pillar | Capability |
|-------|--------|------------|
| Scout | Identify | Threat intel + blind spots → new AttackGenome |
| Forge | Generate | LLM-enriched scam artifacts |
| Critic | Evolve | Feature-aware mutation with reasoning |

## Deliverables

| Artifact | Location |
|----------|----------|
| Code | This repo |
| Walkthrough (.docx) | `docs/AGNI_Solution_Walkthrough.docx` |
| Web prototype | `make api` → http://localhost:8000 |

## Results (IEEE-CIS calibrated, multi-seed)

| Metric | Value |
|--------|-------|
| ROC AUC | 0.997 |
| Sentinel recall | 90.0% |
| Static rules recall | 1.6% |
| FPR | 0.42% |
| Time-to-Evade | 4 generations |
| Attack vectors | 38 (13 tier-A) |
| Agent log entries/run | ~14 |

Full data: [`runs/benchmarks.json`](runs/benchmarks.json)

## Architecture

```
Scout → Fraud Genome → Forge/Playbooks → Digital Twin → Fidelity Judge
                              ↓
                         Sentinel ← Critic ← blind spots
                              ↓
                    Rules baseline (comparison)
```

## Demo script (GFF)

1. Confirm **IEEE-CIS calibrated** badge
2. **Agent Council** — Scout + Critic messages
3. **Run generation** — frozen vs retrained AUC chart
4. **Vector heatmap** — per-genome detection rates
5. **Attack Theater** — LLM artifact + SHAP-lite alert
6. **Baseline** — rules 1.6% vs Sentinel 90%

## Reproduction

```bash
make setup
cp train_transaction.csv data/anchor/
make calibrate
make loop ARGS="--generations 5 --seed 7"
make api
make test
```
