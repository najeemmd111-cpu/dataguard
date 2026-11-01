from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_url: str
    docs_dir: Path
    embedder: str          # "fastembed" (real model) or "hashing" (offline stand-in for tests)
    embed_model: str
    rerank_model: str
    candidates: int        # how many results each method passes on to fusion / re-ranking
    # Phase 3B: root-cause agent
    ollama_url: str
    llm_model: str
    max_tool_rounds: int
    readonly_user: str
    readonly_password: str
    price_in_per_mtok: float   # USD per million input tokens (0 for a local model)
    price_out_per_mtok: float


def get_settings() -> Settings:
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://dataguard:dataguard@localhost:5432/dataguard"
        ),
        docs_dir=Path(os.environ.get("DOCS_DIR", ROOT / "docs")),
        embedder=os.environ.get("DG_EMBEDDER", "fastembed"),
        embed_model=os.environ.get("DG_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        rerank_model=os.environ.get("DG_RERANK_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2"),
        candidates=int(os.environ.get("DG_CANDIDATES", "20")),
        ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        llm_model=os.environ.get("DG_LLM_MODEL", "qwen2.5:3b"),
        max_tool_rounds=int(os.environ.get("DG_MAX_TOOL_ROUNDS", "4")),
        readonly_user=os.environ.get("DG_READONLY_USER", "dataguard_agent_ro"),
        readonly_password=os.environ.get("DG_READONLY_PASSWORD", "readonly"),
        price_in_per_mtok=float(os.environ.get("DG_PRICE_IN_PER_MTOK", "0")),
        price_out_per_mtok=float(os.environ.get("DG_PRICE_OUT_PER_MTOK", "0")),
    )
