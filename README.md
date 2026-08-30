# AGNI — Triple-Agent Fraud Wind Tunnel

**Mastercard Innovation Challenge 2026.** Identify → generate → defend, in one loop.

> A payment fraud wind tunnel: Scout invents the next GenAI attack, Forge simulates it on a twin calibrated to real tickets (USD→INR), Critic mutates until a frozen model is stressed, Sentinel retrains.

## Run

```bash
make setup
cp ~/Downloads/train_transaction.csv data/anchor/   # optional
make calibrate
make loop
cd web && npm ci && npm run build   # once; or `make ui-build`
make api    # http://localhost:8000  (serves the React UI from web/dist)
# live UI work: make api  +  make ui  (Vite on :5173, proxies /api)
```

`.env` (local, never commit):

```
# Groq (fast / cheap — recommended)
AGNI_LLM_PROVIDER=groq
AGNI_LLM_API_KEY=gsk_...
AGNI_LLM_MODEL=qwen/qwen3.8-27b
# Cheaper/faster: llama-3.1-8b-instant

# Or DeepSeek:
# AGNI_LLM_PROVIDER=deepseek
# AGNI_LLM_BASE_URL=https://api.deepseek.com
# AGNI_LLM_API_KEY=sk-...
# AGNI_LLM_MODEL=deepseek-chat
```

## Cloud

```bash
# Render: connect this repo, Docker runtime, set the same env vars.
# First paint uses runs/latest.json — no raw IEEE-CIS on the server.
```

See [SUBMISSION.md](SUBMISSION.md) and [docs/KAGGLE_WRITEUP.md](docs/KAGGLE_WRITEUP.md).
