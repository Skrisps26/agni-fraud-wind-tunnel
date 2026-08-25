"""FastAPI backend for the AGNI wind-tunnel prototype.

GET  /                -> dashboard (web/index.html)
GET  /api/state       -> current genomes, generation history, alerts, headline stats
POST /api/loop/run    -> execute N Red Queen generations in-process and return them

State source of truth: an in-process store seeded from runs/latest.json when the
CLI has been used before. The demo flow is: open dashboard, press "Run", watch
the arms race.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from agni.config import load
from agni.genome.schema import load_genomes
from agni.loop.redqueen import _alerts, run_loop

app = FastAPI(title="AGNI - Fraud Wind Tunnel", version="0.1.0")

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
    return JSONResponse({
        "history": _STATE["history"],
        "genomes": _STATE["genomes"],
        "alerts": _STATE["alerts"],
        "tte_generations": _STATE["tte"],
        "loop_gain_auc": _STATE["loop_gain"],
        "fidelity_mean": _STATE["fidelity"],
    })


@app.post("/api/loop/run")
def run(req: RunRequest) -> JSONResponse:
    _ensure_state()
    cfg = load()
    if req.seed is not None:
        cfg.seed = int(req.seed)
    result, extra = run_loop(cfg, generations=max(1, min(int(req.generations), 10)))
    payload = result.to_json()
    _STATE["history"].extend(result.history)
    _STATE["genomes"] = result.genomes_final
    _STATE["alerts"] = _alerts(extra)
    _STATE["tte"] = max(_STATE["tte"], result.tte_generations)
    _STATE["loop_gain"] = result.loop_gain_auc
    _STATE["fidelity"] = result.fidelity_overall
    return JSONResponse({"ok": True, "new_history": result.history,
                         "tte_generations": result.tte_generations,
                         "loop_gain_auc": result.loop_gain_auc,
                         "state": {k: _STATE[k] for k in
                                   ("history", "tte", "loop_gain", "fidelity")}})
