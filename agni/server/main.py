"""FastAPI backend for the AGNI wind-tunnel prototype."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agni.config import load
from agni.genome.schema import load_genomes
from agni.loop.redqueen import _alerts, _artifact_feed, run_loop

app = FastAPI(title="AGNI - Fraud Wind Tunnel", version="0.3.0")

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
RUNS = ROOT / "runs" / "latest.json"

if WEB.exists():
    app.mount("/static", StaticFiles(directory=str(WEB)), name="static")

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
        "mule_graph": data.get("mule_graph", {"nodes": [], "edges": []}),
        "tte": data.get("tte_generations", 0),
        "loop_gain": data.get("loop_gain_auc", 0.0),
        "fidelity": data.get("fidelity_overall", 0.0),
        "loaded": True,
    })


class RunRequest(BaseModel):
    generations: int = 1
    seed: int | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"ok": True})


@app.get("/api/state")
def state() -> JSONResponse:
    _ensure_state()
    last = _STATE["history"][-1] if _STATE["history"] else {}
    cfg = load()
    return JSONResponse({
        "history": _STATE["history"],
        "genomes": _STATE["genomes"],
        "alerts": _STATE["alerts"],
        "artifacts": _STATE["artifacts"],
        "agent_log": _STATE["agent_log"],
        "vector_det_rates": _STATE.get("vector_det_rates") or last.get("vector_det_rates", {}),
        "mule_graph": _STATE.get("mule_graph") or {},
        "tte_generations": _STATE["tte"],
        "loop_gain_auc": _STATE["loop_gain"],
        "fidelity_mean": _STATE["fidelity"],
        "baseline_recall": last.get("baseline_recall"),
        "calibrated": (ROOT / "agni" / "twin" / "calibration.json").exists(),
        "llm_enabled": cfg.llm_enabled,
        "cloud": cfg.cloud,
    })


@app.post("/api/loop/run")
def run(req: RunRequest) -> JSONResponse:
    _ensure_state()
    cfg = load()
    if req.seed is not None:
        cfg.seed = int(req.seed)
    cap = 1 if cfg.cloud else 10
    gens = max(1, min(int(req.generations), cap))
    result, extra = run_loop(cfg, generations=gens)
    base = len(_STATE["history"])
    for i, h in enumerate(result.history):
        h["generation"] = base + i
    _STATE["history"].extend(result.history)
    _STATE["genomes"] = result.genomes_final
    _STATE["alerts"] = _alerts(extra)
    _STATE["artifacts"] = _artifact_feed(extra)
    _STATE["agent_log"] = _STATE.get("agent_log", []) + result.agent_log
    _STATE["vector_det_rates"] = result.vector_det_rates
    _STATE["mule_graph"] = extra.get("mule_graph") or result.mule_graph
    _STATE["tte"] = max(_STATE["tte"], result.tte_generations)
    _STATE["loop_gain"] = result.loop_gain_auc
    _STATE["fidelity"] = result.fidelity_overall
    last = result.history[-1] if result.history else {}
    return JSONResponse({"ok": True, "new_history": result.history,
                         "agent_log": result.agent_log,
                         "tte_generations": result.tte_generations,
                         "loop_gain_auc": result.loop_gain_auc,
                         "baseline_recall": last.get("baseline_recall")})
