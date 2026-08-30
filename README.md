# AGNI — Triple-Agent Fraud Wind Tunnel

**Mastercard Innovation Challenge 2026.** Identify → generate → defend, in one loop.

> A payment fraud wind tunnel: Scout invents the next GenAI attack, Forge simulates it on a twin calibrated to real tickets (USD→INR), Critic mutates until a frozen model is stressed, Sentinel retrains.

## Run

```bash
make setup
cp ~/Downloads/train_transaction.csv data/anchor/   # optional
make calibrate
make loop
make api    # http://localhost:8000
```

`.env` (local, never commit):

```
AGNI_LLM_PROVIDER=deepseek
AGNI_LLM_BASE_URL=https://api.deepseek.com
AGNI_LLM_API_KEY=sk-...
AGNI_LLM_MODEL=deepseek-chat
```

## Cloud

```bash
# Render: connect this repo, Docker runtime, set the same env vars.
# First paint uses runs/latest.json — no raw IEEE-CIS on the server.
```

See [SUBMISSION.md](SUBMISSION.md) and [docs/KAGGLE_WRITEUP.md](docs/KAGGLE_WRITEUP.md).
