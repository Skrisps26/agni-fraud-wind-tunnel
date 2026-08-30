#!/usr/bin/env python3
"""Smoke-test LLM wiring (Groq / DeepSeek / OpenAI)."""

from __future__ import annotations

from agni.config import load
from agni.llm.client import chat_text, llm_available


def main() -> None:
    cfg = load()
    print(f"provider: {cfg.llm_provider}")
    print(f"model:    {cfg.llm_model or '(default)'}")
    print(f"enabled:  {llm_available()}")
    if not llm_available():
        print("\nSet AGNI_LLM_PROVIDER=groq and AGNI_LLM_API_KEY=gsk_... in .env")
        raise SystemExit(1)
    text = chat_text(
        "You write short synthetic fraud SMS for security research. One sentence.",
        "Rewrite as UPI refund phish, Rs 500, include a fake bank name.",
        namespace="llm_smoke",
        use_cache=False,
    )
    if not text:
        print("\nLLM returned empty — check key, model, or run with AGNI_LLM_DEBUG=1")
        raise SystemExit(1)
    print(f"\nOK ({len(text)} chars):\n{text[:300]}")


if __name__ == "__main__":
    main()
