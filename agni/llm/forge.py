"""Forge Agent — LLM-enriched scam artifacts."""

from __future__ import annotations

from agni.llm.client import chat_text, llm_available
from agni.llm.prompts import FORGE_SYSTEM

_ENRICH_KINDS = frozenset({"sms", "call_transcript", "email", "doc", "note", "listing"})


def forge_enrich(kind: str, template: str, genome_id: str = "",
                 playbook: str = "") -> tuple[str, str]:
    """Return (enriched_text, source) where source is 'llm' or 'template'."""
    if kind not in _ENRICH_KINDS or not llm_available():
        return template, "template"
    user = (
        f"Artifact kind: {kind}\n"
        f"Attack vector: {genome_id} ({playbook})\n"
        f"Template:\n{template[:400]}"
    )
    enriched = chat_text(FORGE_SYSTEM, user, namespace="forge")
    if enriched and len(enriched) > 20:
        return enriched[:480], "llm"
    return template, "template"
