# AGNI — Mastercard Innovation Challenge 2026

## Summary

AGNI is a **Fraud Wind Tunnel**: a closed-loop adversarial AI system that identifies 35 GenAI-powered payment fraud vectors, simulates them with fidelity scored against real IEEE-CIS data, and hardens a fusion detector through a Red Queen evolutionary loop.

**Key novelty:** Time-to-Evade (TtE) metric — measures how many generations a frozen defender survives before evolving attacks bypass it.

## Results

- **35 attack vectors** across UPI, card, wire, wallet
- **ROC AUC 0.997**, recall 92%, FPR 0.41%
- **TtE: 4 generations** (adversarial robustness)
- **Fidelity 0.62** vs real payment marginals

## Links

- **GitHub:** (add repo URL after push)
- **Walkthrough:** `docs/AGNI_Solution_Walkthrough.docx`
- **Demo:** `make setup && make api` → http://localhost:8000

## Three Pillars

1. **Identify** — Fraud Genome: 35 machine-readable attack vectors with TTPs and observables
2. **Generate** — Attack Foundry + Digital Twin + Fidelity Judge (10 playbooks)
3. **Defend** — Sentinel fusion detector with SHAP-lite explanations and FPR budget

## India Relevance

UPI voice-clone scams, digital arrest deepfakes, NPCI impersonation, QR collect-request confusion, agentic checkout abuse — tailored for GFF Mumbai audience.
