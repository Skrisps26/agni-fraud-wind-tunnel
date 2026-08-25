# Solution Walkthrough - source outline (converts to the required .docx)

Target: Mastercard Innovation Challenge 2026 - "AI Defense Lab for Payment
Security". Deadline Aug 31, 2026.

## 1. Executive summary
- One paragraph: fire-with-fire framing; wind-tunnel concept; headline numbers
  from the final run (AUC/recall/FPR, fidelity vs real anchor, TtE).

## 2. The threat landscape we identified
- Grounding stats: FBI $893M AI-fraud losses 2025; India digital-arrest losses;
  agentic-commerce launch surface (Agent Pay / Trusted Agent Protocol).
- The Fraud Genome: schema description; table of shipped vectors x
  (rail, surface, GenAI capability); how the Critic grows the set.

## 3. Real-data grounding (answer to "where does data come from")
- IEEE-CIS/Vesta anchor: what we fit (amount log-normal params, hour shape,
  per-product medians); fx normalization; license handling.
- Fidelity Judge v2: KS distance of simulated attacks vs REAL marginals;
  report per-vector fidelity table.

## 4. How the system generates attacks (fidelity)
- Digital twin composition; calibration flow (calibration.json).
- Playbook execution example narrated end-to-end (GEN-002 digital arrest:
  transcript artifact -> escalating transfers -> layering).
- Judge scores before/after calibration.

## 5. Detection and mitigation (efficacy)
- Feature families; fusion architecture; threshold policy under FPR budget.
- Results per generation: precision / recall / F1 / AUC / FPR (multi-seed).
- Adversarial robustness: frozen-defender decay curve, Time-to-Evade,
  Loop Gain; what mutation taught us about blind spots.

## 6. Real-world feasibility in live payments
- Wind tunnel = model stress-test harness for issuers/acquirers; labeled-data
  factory without PII exposure; analyst console with explanations; integration
  path (score API + streaming features); governance guardrails.

## 7. Demo script (GFF)
- Open dashboard -> run generation live -> arms race chart moves -> walk a
  flagged digital-arrest case in Attack Theater -> genome lineage tree.

## Appendix
- Reproduction instructions (make setup / calibrate / loop), config reference,
  full genome JSON listing.
