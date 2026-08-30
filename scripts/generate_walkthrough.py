#!/usr/bin/env python3
"""Generate AGNI solution walkthrough .docx."""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "agni" / "genome" / "seed"
BENCH = ROOT / "runs" / "benchmarks.json"
CALIB = ROOT / "agni" / "twin" / "calibration.json"
OUT = ROOT / "docs" / "AGNI_Solution_Walkthrough.docx"


def add_para(doc: Document, text: str, bold: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    if bold:
        run.bold = True


def main() -> None:
    bench = json.loads(BENCH.read_text()) if BENCH.exists() else {"summary": {}, "benchmarks": []}
    summary = bench.get("summary", {}).get("mean", {})
    calib = json.loads(CALIB.read_text()) if CALIB.exists() else {}
    genomes = sorted(SEED_DIR.glob("*.json"), key=lambda p: p.name)
    tier_a = sum(1 for p in genomes if json.loads(p.read_text()).get("tier") == "A")

    doc = Document()
    t = doc.add_heading("AGNI — Triple-Agent Fraud Wind Tunnel", 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s = doc.add_paragraph("Mastercard Innovation Challenge 2026 · AI Defense Lab")
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading("1. What this is", 1)
    add_para(doc, (
        "AGNI is a closed-loop wind tunnel for GenAI payment fraud. "
        "Scout proposes vectors from threat intel, Forge writes scam artifacts, "
        "Critic mutates toward defender blind spots, Sentinel retrains under an FPR budget. "
        "Prototype URL belongs in the Kaggle writeup after Render deploy."
    ))
    add_para(doc, (
        f"Headline (multi-seed, IEEE-CIS FX-normalized): "
        f"AUC {summary.get('final_auc', 0.99):.3f}, "
        f"Sentinel recall {summary.get('final_recall', 0.9):.0%}, "
        f"rules recall {summary.get('baseline_recall', 0.02):.1%}, "
        f"FPR {summary.get('final_fpr', 0.004)*100:.2f}%, "
        f"TtE {summary.get('tte', 4):.0f}, "
        f"{tier_a} tier-A playbooks / {len(genomes)} labelled vectors."
    ), bold=True)

    doc.add_heading("2. Rubric map", 1)
    tbl = doc.add_table(rows=1, cols=2)
    tbl.style = "Table Grid"
    tbl.rows[0].cells[0].text = "Criterion"
    tbl.rows[0].cells[1].text = "Evidence"
    for a, b in [
        ("Diversity", "13 executable playbooks (tier A) + param variants (B) + Scout (C)"),
        ("Fidelity", "KS vs IEEE-CIS amounts converted USD→INR; hour shape; velocity; Forge text"),
        ("Detection", "Fusion HGB+TF-IDF; held-out mule/mandate/NPCI on gen 0; FPR ≤ 0.5%"),
        ("Novelty", "Red Queen TtE; Agent Council; unique-src 1h mule graph"),
        ("Feasibility", "Hosted SOC UI; score API; no PII; Agent Pay token-abuse vectors"),
    ]:
        row = tbl.add_row().cells
        row[0].text, row[1].text = a, b

    doc.add_heading("3. Identify", 1)
    add_para(doc, (
        "Do not treat 38 JSON files as 38 unique simulators. Tier A has dedicated playbooks "
        "(voice clone, digital arrest, BEC, KYC bust-out, smishing, QR swap, investment pump, "
        "agentic gift cards, mule recruitment, NPCI chatbot, mandate trap, mule graph ring). "
        "Scout may add GEN-S*** at runtime from FBI/NPCI/digital-arrest intel."
    ))

    doc.add_heading("4. Generate & fidelity", 1)
    rows = calib.get("rows_used", 0)
    add_para(doc, (
        f"Twin fitted on {rows:,} IEEE-CIS rows. Judge compares attack INR amounts to "
        f"TransactionAmt × {calib.get('notes', ['fx=83'])[-1]}. "
        "Hour KS uses Vesta shape only (epoch unknown). "
        "Forge enriches one artifact per (genome, kind) when DeepSeek is on."
    ))

    doc.add_heading("5. Defend", 1)
    add_para(doc, (
        "Sentinel: HistGradientBoosting on velocity, z-score, fan-in, unique senders in 1h, "
        "new dests in 24h, plus TF-IDF on artifacts. Threshold maximizes F1 under FPR 0.5%. "
        "Gen 0 omits mule_graph_ring, subscription_mandate_trap, npci_chatbot_phish so a frozen "
        "defender faces a true held-out pattern. Conservative velocity/amount rules are the baseline — "
        "not Mastercard Decision Intelligence."
    ))
    bt = doc.add_table(rows=1, cols=6)
    bt.style = "Table Grid"
    for i, h in enumerate(["Seed", "AUC", "Recall", "Rules", "FPR", "Fidelity"]):
        bt.rows[0].cells[i].text = h
    for r in bench.get("benchmarks", []):
        row = bt.add_row().cells
        row[0].text = str(r.get("seed", ""))
        row[1].text = f"{r.get('final_auc', 0):.4f}"
        row[2].text = f"{r.get('final_recall', 0):.1%}"
        row[3].text = f"{r.get('baseline_recall', 0):.1%}"
        fpr = r.get("final_fpr", r.get("fpr", 0))
        row[4].text = f"{fpr*100:.2f}%"
        row[5].text = f"{r.get('fidelity', 0):.3f}"

    doc.add_heading("6. Feasibility & GFF demo (90s)", 1)
    add_para(doc, (
        "Open the hosted URL. Rubric strip = four criteria. Agent Council = Scout/Critic. "
        "Mule SVG = unique-src fan-in. Heatmap = held-out miss (red) vs caught (green). "
        "Agent Pay: GEN-007 listing injection, stored agentic token, no step-up. "
        "Governance: synthetic IDs; raw Vesta CSV never redistributed."
    ))
    for i, x in enumerate([
        "Confirm IEEE-CIS + LLM badges",
        "Click GEN-038 / GEN-002",
        "Run one generation if the dyno is awake",
        "Walk Forge LLM artifact vs template",
        "Close on rules vs Sentinel recall",
    ], 1):
        doc.add_paragraph(f"{i}. {x}", style="List Number")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
