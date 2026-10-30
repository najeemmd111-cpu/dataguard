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
    )
