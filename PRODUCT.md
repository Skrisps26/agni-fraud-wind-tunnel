# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary:** Kaggle and Mastercard Innovation Challenge 2026 judges evaluating the AI Defense Lab submission. They arrive with limited time, no narrator, and need to understand **Identify → Generate → Defend** within seconds, then explore evidence (metrics, replay, agent log) if interested.

**Secondary (inferred):** Internal fraud/ML teams reusing the prototype as a demo shell — not the optimization target for this submission window.

## Product Purpose

AGNI is a closed-loop **payment fraud wind tunnel**. It catalogues novel attack vectors (Identify), simulates kill chains on a calibrated digital twin with optional LLM-forged artifacts (Generate / Forge), runs Scout/Critic mutation (Loop), and measures a trained Sentinel model against a straw rules checklist (Defend).

Success for the submission: judges can name the three pillars, see a working hosted prototype, and trust the metrics story (ROC AUC, recall, twin fidelity, time-to-evade, rules baseline gap) without over-claimed production integration.

## Positioning

Held-out digital twin + Red Queen loop that stress-tests detection **before** attacks reach production — combining graph-shaped observables (mule fan-in), GenAI artifact simulation, and frozen-model evasion measurement. Not a static fraud dashboard, not a rules-engine product pitch, not a claim of Mastercard production DI deployment.

## Operating Context

- **Submission deadline:** Aug 31, 2026 (Mastercard Innovation Challenge 2026).
- **Deliverables:** GitHub repo, hosted web prototype, walkthrough doc (`docs/AGNI_Solution_Walkthrough.docx` — path referenced in SUBMISSION.md), Kaggle writeup (`docs/KAGGLE_WRITEUP.md`).
- **Local dev:** `make setup` → optional `make calibrate` → `make loop` → `make ui-build` → `make api` at `:8000`.
- **Live UI dev:** `make api` + `make ui` (Vite `:5173`, proxies `/api`).
- **Cloud:** Docker/Render; first paint from seeded `runs/latest.json` — no raw IEEE-CIS on server.
- **Optional LLM:** Groq or DeepSeek via `.env`; offline runs (`AGNI_LLM_PROVIDER=none`) must remain fully demoable.

## Capabilities and Constraints

**Capabilities (confirmed in repo):**

- Triple-agent loop: Scout (invent), Forge (simulate + LLM artifacts), Critic (mutate), Sentinel (retrain/detect).
- 13+ tier-A playbooks; Scout tier-C; Agent Pay vectors (e.g. GEN-007/018/029).
- IEEE-CIS anchor with USD→INR FX scaling for twin fidelity (KS on amounts).
- Sentinel: HistGradientBoosting + TfidfVectorizer + LogisticRegression fusion.
- Rules baseline: velocity/amount checklist — explicitly **not** production Mastercard rules.
- Web UI: four panes (Identify, Generate→Defend replay, Loop council, Defend charts/heatmap).
- API: FastAPI `/api/state`, `/api/loop/run`; serves `web/dist`.

**Constraints (must preserve in copy and UI):**

- Synthetic IDs only; no raw PII.
- Rules baseline labeled as straw checklist, not Mastercard production.
- Do not claim 38 unique attack engines or production Decision Intelligence integration.
- FPR budget 0.5%; responsible-use framing for TTP-level playbooks.
- LLM artifacts optional; seeded `runs/latest.json` must power full demo without API keys.

**Terminology:**

| Term | Meaning |
|------|---------|
| Genome / vector | Attack playbook ID (e.g. GEN-006) |
| Twin fidelity | KS vs INR-scaled IEEE-CIS reference |
| Time to evade | Generations a frozen model survives under mutation |
| Sentinel | Trained fraud classifier (not production MC system) |

**Open decisions:**

- Live Render URL not yet recorded in SUBMISSION.md.
- Walkthrough `.docx` referenced but may still need generation.

## Brand Commitments

- **Name:** AGNI (Triple-Agent Fraud Wind Tunnel).
- **Tagline:** Identify → generate → detect → mutate.
- **Voice:** Direct, technical, honest about baselines and synthetic data. No hype about production deployment.
- **Repo:** https://github.com/Skrisps26/agni-fraud-wind-tunnel

## Evidence on Hand

| Asset | Path / note |
|-------|-------------|
| Seeded loop output | `runs/latest.json` (metrics, genomes, demo_chains, atlas, protocol, shadow) |
| Honest eval | `make eval-honest` / `runs/protocol.json` |
| Atlas | `make atlas` |
| Shadow one-pager | `docs/SHADOW_MODE.md` |
| Benchmarks | `runs/benchmarks.json` |
| LLM cache | `runs/llm_cache.json` |
| Twin calibration | `agni/twin/calibration.json` (when calibrated) |
| Kaggle writeup | `docs/KAGGLE_WRITEUP.md` |
| Submission checklist | `SUBMISSION.md` |
| Design system (visual) | `web/DESIGN.md` — product truth lives here only for visual decisions |

**Do not fabricate:** customer logos, production Mastercard integration claims, live Render URL, or benchmark numbers not present in `runs/`.

## Product Principles

1. **Show the loop, not slides** — the prototype must demonstrate Identify → Generate → Defend without narration.
2. **Honest baselines** — rules checklist is a straw man; Sentinel is a research model, not production.
3. **Synthetic by design** — all identities and transactions are simulated; say so plainly.
4. **Evidence over adjectives** — lead with replay, heatmap, and frozen-AUC story, not vector counts.
5. **Offline-first demo** — judges must get a full experience from seeded data if LLM keys are absent.

## Accessibility & Inclusion

No product-specific WCAG target established. Future surfaces should maintain keyboard focus, semantic headings, and `aria-live` on dynamic replay/scoreboard regions (partially implemented in web UI).
