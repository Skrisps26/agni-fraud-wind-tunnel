# AGNI — Triple-Agent Fraud Wind Tunnel

**Mastercard Innovation Challenge 2026** — closed-loop adversarial AI for GenAI payment fraud.

> *"We don't just detect GenAI fraud — we measure how fast it evades you, then close the gap."*

## Triple-Agent Council

| Agent | Pillar | Role |
|-------|--------|------|
| **Scout** | Identify | Discovers new attack vectors from threat intel + blind spots |
| **Forge** | Generate | LLM-enriches scam artifacts (DeepSeek / offline fallback) |
| **Critic** | Evolve | Reasons about evasion; drives feature-aware mutation |

**Calibrated on IEEE-CIS** (590K real transactions). **38 attack vectors** (13 tier-A playbooks).

**Headline results:** AUC **0.997**, Sentinel recall **90%**, static rules **1.6%**, TtE **4 gens**.

```bash
make setup
cp ~/Downloads/train_transaction.csv data/anchor/   # one-time
make calibrate
make loop
make api    # → http://localhost:8000
```

## DeepSeek (optional)

```bash
# .env
AGNI_LLM_PROVIDER=deepseek
AGNI_LLM_BASE_URL=https://api.deepseek.com
AGNI_LLM_API_KEY=sk-...
AGNI_LLM_MODEL=deepseek-chat
```

## Submission artifacts

- **Repo:** https://github.com/Skrisps26/agni-fraud-wind-tunnel
- **Walkthrough:** `docs/AGNI_Solution_Walkthrough.docx`
- **Demo:** `make api`

See [SUBMISSION.md](SUBMISSION.md) for full evaluation table.
