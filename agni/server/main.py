"""FastAPI backend for the AGNI wind-tunnel prototype."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from agni.config import load
from agni.genome.schema import load_genomes
from agni.loop.redqueen import _alerts, _artifact_feed, run_loop

app = FastAPI(title="AGNI - Fraud Wind Tunnel", version="0.2.0")

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
RUNS = ROOT / "runs" / "latest.json"

_STATE: dict = {"loaded": False}


def _ensure_state() -> None:
    if _STATE["loaded"]:
        return
    try:
        data = json.loads(RUNS.read_text())
    except Exception:
        data = {}
    _STATE.update({
        "history": data.get("history", []),
        "genomes": data.get("genomes_final",
                            [json.loads(g.model_dump_json()) for g in load_genomes()]),
        "alerts": data.get("alerts", []),
        "artifacts": data.get("artifacts", []),
        "agent_log": data.get("agent_log", []),
        "vector_det_rates": data.get("vector_det_rates", {}),
        "tte": data.get("tte_generations", 0),
        "loop_gain": data.get("loop_gain_auc", 0.0),
        "fidelity": data.get("fidelity_overall", 0.0),
        "loaded": True,
    })


class RunRequest(BaseModel):
    generations: int = 2
    seed: int | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/api/state")
def state() -> JSONResponse:
    _ensure_state()
    last = _STATE["history"][-1] if _STATE["history"] else {}
    return JSONResponse({
        "history": _STATE["history"],
        "genomes": _STATE["genomes"],
        "alerts": _STATE["alerts"],
        "artifacts": _STATE["artifacts"],
        "agent_log": _STATE["agent_log"],
        "vector_det_rates": _STATE.get("vector_det_rates") or last.get("vector_det_rates", {}),
        "tte_generations": _STATE["tte"],
        "loop_gain_auc": _STATE["loop_gain"],
        "fidelity_mean": _STATE["fidelity"],
        "baseline_recall": last.get("baseline_recall"),
        "calibrated": (ROOT / "agni" / "twin" / "calibration.json").exists(),
    })


@app.post("/api/loop/run")
def run(req: RunRequest) -> JSONResponse:
    _ensure_state()
    cfg = load()
    if req.seed is not None:
        cfg.seed = int(req.seed)
    result, extra = run_loop(cfg, generations=max(1, min(int(req.generations), 10)))
    base = len(_STATE["history"])
    for i, h in enumerate(result.history):
        h["generation"] = base + i
    _STATE["history"].extend(result.history)
    _STATE["genomes"] = result.genomes_final
    _STATE["alerts"] = _alerts(extra)
    _STATE["artifacts"] = _artifact_feed(extra)
    _STATE["agent_log"] = _STATE.get("agent_log", []) + result.agent_log
    _STATE["vector_det_rates"] = result.vector_det_rates
    _STATE["tte"] = max(_STATE["tte"], result.tte_generations)
    _STATE["loop_gain"] = result.loop_gain_auc
    _STATE["fidelity"] = result.fidelity_overall
    last = result.history[-1] if result.history else {}
    return JSONResponse({"ok": True, "new_history": result.history,
                         "agent_log": result.agent_log,
                         "tte_generations": result.tte_generations,
                         "loop_gain_auc": result.loop_gain_auc,
                         "state": {k: _STATE[k] for k in
                                   ("history", "artifacts", "agent_log", "vector_det_rates",
                                    "tte", "loop_gain", "fidelity")},
                         "baseline_recall": last.get("baseline_recall")})
