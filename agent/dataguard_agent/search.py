"""The four retrieval methods compared by the evaluation."""

from __future__ import annotations

from dataclasses import replace

import psycopg

from .models import Embedder, Reranker
from .store import Hit, keyword_search, vector_search

METHODS = ("keyword", "vector", "hybrid", "hybrid_rerank")

RRF_K = 60  # standard constant from the Reciprocal Rank Fusion paper (Cormack et al., 2009)


def reciprocal_rank_fusion(*rankings: list[Hit], k: int = RRF_K) -> list[Hit]:
    """Merge ranked lists: each list gives a chunk 1 / (k + rank). Scores need not be comparable."""
    scores: dict[str, float] = {}
    first_seen: dict[str, Hit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(hit.chunk_id, hit)
    fused = [replace(first_seen[cid], score=s) for cid, s in scores.items()]
    fused.sort(key=lambda h: (-h.score, h.chunk_id))
    return fused


class Searcher:
    def __init__(self, conn: psycopg.Connection, embedder: Embedder, reranker: Reranker | None, candidates: int = 20):
        self.conn = conn
        self.embedder = embedder
        self.reranker = reranker
        self.candidates = candidates

    def search(self, query: str, method: str = "hybrid_rerank", limit: int = 5) -> list[Hit]:
        if method == "keyword":
            return keyword_search(self.conn, query, limit)
        if method == "vector":
            return vector_search(self.conn, self.embedder.embed_query(query), limit)

        n = self.candidates
        fused = reciprocal_rank_fusion(
            keyword_search(self.conn, query, n),
            vector_search(self.conn, self.embedder.embed_query(query), n),
        )
        if method == "hybrid":
            return fused[:limit]
        if method == "hybrid_rerank":
            if self.reranker is None:
                raise ValueError("hybrid_rerank needs a reranker")
            pool = fused[:n]
            scores = self.reranker.scores(query, [h.text for h in pool])
            reranked = [replace(h, score=s) for h, s in zip(pool, scores)]
            reranked.sort(key=lambda h: (-h.score, h.chunk_id))
            return reranked[:limit]
        raise ValueError(f"unknown method {method!r}; choose from {', '.join(METHODS)}")
