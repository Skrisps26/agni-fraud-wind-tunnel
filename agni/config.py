"""Central configuration. Env vars override defaults; no config file needed."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


_load_dotenv()


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


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
    llm_provider: str = field(default_factory=lambda: os.environ.get("AGNI_LLM_PROVIDER", "none"))
    llm_api_key: str = field(default_factory=lambda: os.environ.get("AGNI_LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.environ.get("AGNI_LLM_MODEL", ""))
    llm_base_url: str = field(default_factory=lambda: os.environ.get("AGNI_LLM_BASE_URL", ""))

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider not in ("", "none") and bool(self.llm_api_key)


def load() -> Config:
    return Config()
