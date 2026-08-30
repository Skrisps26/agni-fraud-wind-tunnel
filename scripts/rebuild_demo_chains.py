#!/usr/bin/env python3
"""Rebuild demo_chains in runs/latest.json without a full LLM loop (~30s)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from agni.config import load
from agni.loop.redqueen import _build_demo_chains, run_loop

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "runs" / "latest.json"


def main() -> None:
    os.environ.setdefault("AGNI_LLM_PROVIDER", "none")
    cfg = load()
    print("Rebuilding demo playback (LLM off, 1 generation)...")
    result, extra = run_loop(cfg, generations=1, verbose=True)
    chains = _build_demo_chains(extra, extra.get("genome_of") or {})
    if LATEST.exists():
        payload = json.loads(LATEST.read_text())
    else:
        payload = result.to_json()
    payload.update({
        "history": result.history,
        "genomes_final": result.genomes_final,
        "agent_log": result.agent_log,
        "demo_chains": chains,
    })
    LATEST.write_text(json.dumps(payload, indent=1))
    print(f"Wrote {len(chains)} demo chains to {LATEST}")


if __name__ == "__main__":
    main()
