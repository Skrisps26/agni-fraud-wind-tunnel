# AGNI — Triple-Agent Fraud Wind Tunnel

Mastercard Innovation Challenge 2026 · AI Defense Lab for Payment Security

AGNI is a **wind tunnel + scoring protocol**. Sentinel is one occupant of the tunnel, not the product.

**Live demo:** https://agni-fraud-wind-tunnel.onrender.com  
**Code:** https://github.com/Skrisps26/agni-fraud-wind-tunnel

## Criterion map

| Judge criterion | Where it lives | Honest claim |
|-----------------|----------------|--------------|
| Diversity | Fraud Genome Atlas (`make atlas`) — 13 tier-A families, not 38 unique engines. Empty cells are documented holes. Scout **compiles** a Foundry playbook or the genome is not Identify. | Coverage + TTP distance, not JSON count. |
| Fidelity | IEEE-CIS FX→INR **amount/hour** plus joint MMD on (log amount, hour). UPI-shaped Zipf merchants, collect vs pay. Target **0.2% fraud** for reported metrics (lab still oversamples for training). | IEEE ≠ NPCI microdata. |
| Detection | Lab AUC is **not** the headline. Report **family-holdout AUC**, **recall at 0.2% base rate**, frozen **time-to-evade**, graph/sequence/tabular ablation, IsolationForest occupant. Straw rules + bank checklist labeled non-Mastercard. | Circularity is named and measured. |
| Novelty | Time-to-Evade under a frozen model at published FPR; occupancy API (`POST /api/occupancy`); league table per generation. | Closed-loop measurement, not a new transformer. |
| Feasibility | [docs/SHADOW_MODE.md](SHADOW_MODE.md) — shadow, FPR tripwire, feature contract, synthetic-only. | Lab, not live DI. |

## Thesis

Scout invents/compiles the next GenAI attack, Forge simulates it on a twin, Critic mutates until a **frozen** model is stressed, Sentinel retrains. Graph-shaped observables (unique senders into a sink in 1h) match Decision Intelligence mule-ring features. Agentic checkout (GEN-007/018/029) matches Agent Pay: stored token, no step-up, prompt-injected listing.

## Kill-chain (GEN-002)

Deepfake video-call artifact → escalating UPI → mule layering → Sentinel → Critic slows the burst. Held-out families (`mule_graph_ring`, `subscription_mandate_trap`, `npci_chatbot_phish`) are **absent from gen-0 training**.

## Reproduce

```
make setup
cp train_transaction.csv data/anchor/   # optional
make twin
make atlas
make eval-honest
make loop ARGS='--generations 5'
make api
```

## Responsible use

Synthetic identities only. Playbooks are TTP-level research artifacts. Rules/checklist baselines are **not** Mastercard production.
