"""Central configuration. Env vars override defaults; no config file needed."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _strip_val(v: str) -> str:
    v = v.strip().strip('"').strip("'")
    if "#" in v:
        v = v.split("#", 1)[0].strip()
    return v


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), _strip_val(v))


_load_dotenv()


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, default)
    return int(_strip_val(str(raw)) if not isinstance(raw, int) else raw)


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, default)
    return float(_strip_val(str(raw)) if not isinstance(raw, float) else raw)


@dataclass
class Config:
    # --- simulation scale ---
    seed: int = field(default_factory=lambda: _int("AGNI_SEED", 7))
    consumers: int = field(default_factory=lambda: _int("AGNI_CONSUMERS", 1200))
    merchants: int = field(default_factory=lambda: _int("AGNI_MERCHANTS", 140))
    days: int = field(default_factory=lambda: _int("AGNI_DAYS", 10))

    # --- background traffic ---
    daily_txn_lambda: float = field(
        default_factory=lambda: _float("AGNI_DAILY_LAMBDA", 1.15)
    )
    benign_msg_cap: int = field(default_factory=lambda: _int("AGNI_BENIGN_MSG_CAP", 2500))
    target_fraud_rate: float = field(
        default_factory=lambda: _float("AGNI_TARGET_FRAUD_RATE", 0.002)
    )

    # --- foundry ---
    runs_per_genome: int = field(default_factory=lambda: _int("AGNI_RUNS_PER_GENOME", 2))
    max_genomes: int = field(default_factory=lambda: _int("AGNI_MAX_GENOMES", 50))

    # --- defense / loop ---
    fpr_budget: float = field(default_factory=lambda: _float("AGNI_FPR_BUDGET", 0.005))
    tte_threshold: float = field(default_factory=lambda: _float("AGNI_TTE_THRESHOLD", 0.90))
    text_blend_weight: float = field(default_factory=lambda: _float("AGNI_TEXT_WEIGHT", 0.20))
    generations: int = field(default_factory=lambda: _int("AGNI_GENERATIONS", 5))
    evasion_gens: int = field(default_factory=lambda: _int("AGNI_EVASION_GENS", 2))
    cloud: bool = field(default_factory=lambda: os.environ.get("AGNI_CLOUD", "").lower()
                        in ("1", "true", "yes") or bool(os.environ.get("RENDER")))
    held_out_playbooks: tuple[str, ...] = (
        "mule_graph_ring", "subscription_mandate_trap", "npci_chatbot_phish",
    )

    # --- optional LLM enrichment ---
    llm_provider: str = field(default_factory=lambda: _llm_provider())
    llm_api_key: str = field(default_factory=lambda: _llm_api_key())
    llm_model: str = field(default_factory=lambda: os.environ.get("AGNI_LLM_MODEL", ""))
    llm_base_url: str = field(default_factory=lambda: _llm_base_url())

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider not in ("", "none") and bool(self.llm_api_key)


def _llm_provider() -> str:
    p = os.environ.get("AGNI_LLM_PROVIDER", "none").strip().lower()
    if p not in ("", "none"):
        return p
    if os.environ.get("GROQ_API_KEY", "").strip():
        return "groq"
    return "none"


def _llm_api_key() -> str:
    key = os.environ.get("AGNI_LLM_API_KEY", "").strip()
    if key:
        return key
    provider = _llm_provider()
    if provider == "groq":
        return os.environ.get("GROQ_API_KEY", "").strip()
    return ""


def _llm_base_url() -> str:
    provider = _llm_provider()
    raw = _strip_val(os.environ.get("AGNI_LLM_BASE_URL", ""))
    defaults = {
        "groq": "https://api.groq.com/openai/v1",
        "deepseek": "https://api.deepseek.com",
        "openai": "https://api.openai.com/v1",
    }
    if not raw:
        return ""
    # Ignore a stale base URL left over from another provider.
    if provider == "groq" and "groq.com" not in raw:
        return ""
    if provider == "deepseek" and "deepseek" not in raw:
        return ""
    if provider == "openai" and "openai.com" not in raw:
        return ""
    return raw


def load() -> Config:
    return Config()
