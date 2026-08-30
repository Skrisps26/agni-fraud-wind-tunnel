"""OpenAI-compatible LLM client (Groq, DeepSeek, OpenAI, etc.)."""

from __future__ import annotations

import json
import logging
import os
import re

from agni.config import load
from agni.llm.cache import cache_key, get, put

log = logging.getLogger("agni.llm")


def llm_available() -> bool:
    return load().llm_enabled


def _client():
    from openai import OpenAI

    cfg = load()
    defaults = {
        "deepseek": "https://api.deepseek.com",
        "groq": "https://api.groq.com/openai/v1",
        "openai": "https://api.openai.com/v1",
    }
    base = cfg.llm_base_url or defaults.get(cfg.llm_provider)
    if not base:
        raise ValueError(f"No API base URL for LLM provider {cfg.llm_provider!r}")
    if not cfg.llm_api_key:
        raise ValueError("LLM API key missing (set AGNI_LLM_API_KEY or GROQ_API_KEY)")
    return OpenAI(api_key=cfg.llm_api_key, base_url=base)


def _model() -> str:
    cfg = load()
    if cfg.llm_model:
        return cfg.llm_model
    defaults = {
        "deepseek": "deepseek-chat",
        "groq": "qwen/qwen3.8-27b",
        "openai": "gpt-4o-mini",
    }
    return defaults.get(cfg.llm_provider, "gpt-4o-mini")


def _completion_params(system: str, user: str) -> dict:
    cfg = load()
    params: dict = {
        "model": _model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.6,
    }
    # Groq Qwen models expect max_completion_tokens (see Groq OpenAI compat docs).
    if cfg.llm_provider == "groq":
        params["max_completion_tokens"] = 512
        params["top_p"] = 0.95
    else:
        params["max_tokens"] = 500
    return params


def chat_text(system: str, user: str, namespace: str = "chat",
              use_cache: bool = True) -> str:
    if not llm_available():
        return ""
    key = cache_key(namespace, system[:40], user)
    if use_cache:
        cached = get(namespace, key)
        if isinstance(cached, str) and cached:
            return cached
    try:
        resp = _client().chat.completions.create(**_completion_params(system, user))
        text = (resp.choices[0].message.content or "").strip()
        if use_cache and text:
            put(namespace, key, text)
        return text
    except Exception as exc:
        log.warning("chat_text failed (%s): %s", _model(), exc)
        if os.environ.get("AGNI_LLM_DEBUG"):
            raise
        return ""


def chat_json(system: str, user: str, namespace: str = "json") -> dict | None:
    if not llm_available():
        return None
    key = cache_key(namespace, system[:40], user)
    cached = get(namespace, key)
    if isinstance(cached, dict):
        return cached
    raw = chat_text(system, user, namespace=namespace, use_cache=False)
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group())
        put(namespace, key, data)
        return data
    except json.JSONDecodeError:
        return None
