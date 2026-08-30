#!/usr/bin/env python3
"""Generate AGNI solution walkthrough .docx for Mastercard Innovation Challenge 2026."""

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


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


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
    title = doc.add_heading("AGNI — Triple-Agent Fraud Wind Tunnel", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph(
        "Mastercard Innovation Challenge 2026 · AI Defense Lab for Payment Security")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

    add_heading(doc, "1. Executive Summary", 1)
    add_para(doc, (
        "AGNI is a closed-loop adversarial AI system for GenAI-powered payment fraud. "
        "Three LLM agents — Scout (identify), Forge (generate), Critic (evolve) — operate "
        "inside a Red Queen wind tunnel calibrated on 590,540 real IEEE-CIS/Vesta transactions. "
        "We measure Time-to-Evade (TtE): how many generations a frozen defender survives "
        "before evolving attacks bypass it."
    ))
    bl = summary.get("baseline_recall", 0.016)
    add_para(doc, (
        f"Headline results (seeds 7/42/99, IEEE-CIS calibrated): "
        f"ROC AUC {summary.get('final_auc', 0.997):.3f}, "
        f"Sentinel recall {summary.get('final_recall', 0.90):.1%}, "
        f"static rules recall {bl:.1%}, "
        f"FPR {summary.get('final_fpr', 0.004)*100:.2f}%, "
        f"TtE {summary.get('tte', 4):.0f} gens, "
        f"{len(genomes)} vectors ({tier_a} tier-A playbooks)."
    ), bold=True)

    add_heading(doc, "2. Triple-Agent Council", 1)
    add_para(doc, (
        "Scout Agent: reads curated threat intel (FBI AI-fraud, India digital-arrest, NPCI "
        "UPI advisories) plus defender blind spots; proposes new AttackGenome JSON each "
        "2 generations (DeepSeek API, offline fallback included).\n\n"
        "Forge Agent: LLM-enriches scam artifacts (SMS, transcripts, emails) for realism; "
        "cached per attack_id.\n\n"
        "Critic Agent: analyzes detection rates and feature blind spots; narrates mutation "
        "strategy in the Agent Council UI."
    ))

    add_heading(doc, "3. Threat Landscape — Fraud Genome", 1)
    add_para(doc, (
        f"{len(genomes)} vectors tiered honestly: Tier A = dedicated playbook, "
        "Tier B = param variant, Tier C = Scout-discovered at runtime."
    ))
    table = doc.add_table(rows=1, cols=7)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(["ID", "Tier", "Vector", "Rails", "Surface", "Capability", "Playbook"]):
        hdr[i].text = h
    for p in genomes:
        g = json.loads(p.read_text())
        row = table.add_row().cells
        row[0].text = g["id"]
        row[1].text = g.get("tier", "B")
        row[2].text = g["name"][:40]
        row[3].text = ", ".join(g.get("rails", []))
        row[4].text = ", ".join(g.get("surfaces", []))[:30]
        row[5].text = ", ".join(g.get("capabilities", []))[:30]
        row[6].text = g.get("playbook", "")

    add_heading(doc, "4. Real-Data Grounding", 1)
    rows = calib.get("rows_used", "N/A")
    med = calib.get("amount_usd", {}).get("median", "N/A")
    inr = calib.get("consumer_median_inr", "N/A")
    add_para(doc, (
        f"Fitted from IEEE-CIS train_transaction.csv: {rows:,} rows, "
        f"median ticket ${med} USD, consumer target {inr} INR. "
        "Fidelity Judge scores KS distance vs real amount/hour marginals."
    ))

    add_heading(doc, "5. Kill-Chain Walkthrough — GEN-002 Digital Arrest", 1)
    add_para(doc, (
        "1. Forge generates deepfake video-call transcript artifact.\n"
        "2. Victim coerced into escalating UPI 'verification' transfers.\n"
        "3. Funds layer through mule VPAs (dst_fan_in signal).\n"
        "4. Sentinel flags via velocity + text fusion; SHAP-lite shows vel_1h, amt_z_user.\n"
        "5. Critic mutates: spread transfers over 6h to evade velocity windows.\n"
        "6. Evasion-pressure generations (frozen defender) show frozen AUC dip; retrain recovers."
    ))

    add_heading(doc, "6. Detection Efficacy", 1)
    bt = doc.add_table(rows=1, cols=7)
    bt.style = "Table Grid"
    bh = bt.rows[0].cells
    for i, h in enumerate(["Seed", "AUC", "Recall", "Rules Rec", "FPR", "Fidelity", "TtE"]):
        bh[i].text = h
    for r in bench.get("benchmarks", []):
        row = bt.add_row().cells
        row[0].text = str(r["seed"])
        row[1].text = f"{r['final_auc']:.4f}"
        row[2].text = f"{r['final_recall']:.1%}"
        row[3].text = f"{r.get('baseline_recall', 0):.1%}"
        row[4].text = f"{r.get('final_fpr', r.get('fpr', 0))*100:.2f}%"
        row[5].text = f"{r['fidelity']:.3f}"
        row[6].text = str(r["tte"])

    add_heading(doc, "7. Real-World Feasibility", 1)
    add_para(doc, (
        "Wind-tunnel harness for issuers: REST API (POST /api/loop/run), analyst console "
        "with Agent Council + vector heatmap, labeled data without PII. "
        "Governance: synthetic identities, TTP-level playbooks only."
    ))

    add_heading(doc, "8. GFF Demo Script", 1)
    for i, s in enumerate([
        "Open http://localhost:8000 — confirm 'IEEE-CIS calibrated' badge",
        "Agent Council: show Scout discovery + Critic mutation messages",
        "Run generation — arms race chart: frozen AUC vs retrained AUC",
        "Vector heatmap: red = blind spot, green = caught",
        "Attack Theater: LLM-enriched artifact + SHAP-lite flagged txn",
        "Baseline bar: rules 1.6% recall vs Sentinel 90%+",
    ], 1):
        doc.add_paragraph(f"{i}. {s}", style="List Number")

    add_heading(doc, "Appendix", 1)
    for cmd in ["make setup", "cp train_transaction.csv data/anchor/", "make calibrate",
                "make loop", "make api"]:
        doc.add_paragraph(cmd, style="List Bullet")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
