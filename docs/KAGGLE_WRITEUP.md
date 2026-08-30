# AGNI — Mastercard Innovation Challenge 2026

## Summary

**AGNI** is a Triple-Agent Fraud Wind Tunnel: Scout discovers attacks, Forge generates realistic scams, Critic evolves evasion — all inside a Red Queen loop calibrated on **590K real IEEE-CIS transactions**.

## Why this wins

- **Real GenAI:** DeepSeek-powered Scout/Forge/Critic (offline fallback included)
- **Real data:** Fidelity scored vs IEEE-CIS marginals, not self-referential
- **Measurable arms race:** TtE, frozen AUC decay, evasion-pressure generations
- **Proof of value:** Sentinel **90%** recall vs static rules **1.6%**
- **India-specific:** UPI, digital arrest, NPCI, agentic checkout — 38 vectors

## Links

- **GitHub:** https://github.com/Skrisps26/agni-fraud-wind-tunnel
- **Walkthrough:** `docs/AGNI_Solution_Walkthrough.docx`
- **Demo:** `make setup && make calibrate && make api`

## Headline numbers

| Metric | Value |
|--------|-------|
| ROC AUC | 0.997 |
| Sentinel recall | 90% |
| Rules baseline recall | 1.6% |
| FPR | 0.42% |
| TtE | 4 generations |
| Vectors | 38 |

## Three pillars

1. **Identify** — Scout Agent + 38 Fraud Genome vectors (tier A/B/C)
2. **Generate** — 13 playbooks + Forge LLM artifacts + Fidelity Judge
3. **Defend** — Sentinel fusion detector + SHAP-lite + rules baseline

## DeepSeek setup (optional, ~$0.50/demo)

```
AGNI_LLM_PROVIDER=deepseek
AGNI_LLM_BASE_URL=https://api.deepseek.com
AGNI_LLM_API_KEY=sk-...
AGNI_LLM_MODEL=deepseek-chat
```
