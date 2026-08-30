# AGNI — Triple-Agent Fraud Wind Tunnel

Mastercard Innovation Challenge 2026 · AI Defense Lab for Payment Security

## Criterion map

| Judge criterion | Where it lives |
|-----------------|----------------|
| Diversity | 13 tier-A playbooks + Scout tier-C; not “38 unique engines” |
| Fidelity | IEEE-CIS tickets **FX-converted USD→INR** before KS; Forge LLM text |
| Detection | Sentinel vs conservative rules; held-out mule/mandate/NPCI on gen 0 |
| Novelty | Red Queen + Agent Council + mule graph (unique-src fan-in) |
| Feasibility | Hosted prototype, FPR budget 0.5%, no PII, Agent Pay vectors |

## Thesis

A payment fraud **wind tunnel**: Scout invents the next GenAI attack, Forge simulates it on a twin calibrated to real tickets, Critic mutates until a frozen model is stressed, Sentinel retrains. Graph-shaped observables (unique senders into a sink in 1h) are what Decision Intelligence already uses on mule rings. Agentic checkout vectors (GEN-007/018/029) match Agent Pay: stored token, no step-up, prompt-injected listing.

## Kill-chain (GEN-002)

Deepfake video-call artifact → escalating UPI “verification” → mule layering → Sentinel (velocity + text) → Critic slows the burst. Held-out GEN-038 (mule ring) is **absent from gen-0 training**, then injected so frozen AUC / heatmap can show a real miss.

## Reproduce

```
make setup
cp train_transaction.csv data/anchor/
make calibrate
make loop
make api
```

DeepSeek (optional): set AGNI_LLM_* in `.env`. Cloud: `AGNI_CLOUD=1` + Dockerfile.

## Responsible use

Synthetic identities only. Playbooks are TTP-level research artifacts.
