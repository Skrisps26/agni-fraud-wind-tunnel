"""CLI: print honest protocol metrics from a ledger run or latest.json."""

from __future__ import annotations

import json
from pathlib import Path

from agni.config import load
from agni.genome.atlas import coverage_matrix
from agni.loop.redqueen import run_loop


def main() -> None:
    cfg = load()
    cfg.generations = 1
    result, _ = run_loop(cfg, generations=1, verbose=True)
    atlas = coverage_matrix()
    proto = result.protocol
    print(json.dumps({
        "disclaimer": proto.get("headline"),
        "lab_auc": (result.history[-1] or {}).get("roc_auc"),
        "protocol": proto,
        "tte": result.tte_generations,
        "atlas": {k: atlas[k] for k in ("n_families", "n_tier_a", "coverage", "diversity", "holes")},
    }, indent=2))
    out = Path("runs") / "protocol.json"
    out.write_text(json.dumps({"protocol": proto, "atlas": atlas, "shadow": result.shadow}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
