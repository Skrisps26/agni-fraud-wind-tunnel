"""OpenAI-compatible LLM client (DeepSeek, OpenAI, etc.)."""

from __future__ import annotations

import json
import re

from agni.config import load
from agni.llm.cache import cache_key, get, put


def llm_available() -> bool:
    return load().llm_enabled


def _client():
    from openai import OpenAI
    cfg = load()
    base = cfg.llm_base_url or None
    if cfg.llm_provider == "deepseek" and not base:
        base = "https://api.deepseek.com"
    return OpenAI(api_key=cfg.llm_api_key, base_url=base)


def _model() -> str:
    cfg = load()
    if cfg.llm_model:
        return cfg.llm_model
    if cfg.llm_provider == "deepseek":
        return "deepseek-chat"
    return "gpt-4o-mini"


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
        resp = _client().chat.completions.create(
            model=_model(),
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.7,
            max_tokens=500,
        )
        text = (resp.choices[0].message.content or "").strip()
        if use_cache and text:
            put(namespace, key, text)
        return text
    except Exception:
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
