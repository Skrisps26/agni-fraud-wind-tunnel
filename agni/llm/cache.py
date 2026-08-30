"""Disk cache for LLM responses — keeps demo cost low and enables offline replay."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "runs" / "llm_cache.json"


def _load() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return {}


def _save(data: dict) -> None:
    CACHE_PATH.parent.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data, indent=1))


def get(namespace: str, key: str) -> str | dict | None:
    return _load().get(f"{namespace}:{key}")


def put(namespace: str, key: str, value: str | dict) -> None:
    data = _load()
    data[f"{namespace}:{key}"] = value
    _save(data)


def cache_key(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
