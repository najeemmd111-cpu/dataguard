"""Embedding and re-ranking models.

Real models run through fastembed (ONNX Runtime: no PyTorch, ~90 MB per model,
downloaded from Hugging Face on first use). The hashing embedder is a small
offline stand-in so tests run without downloads; it is not used for results.
"""

from __future__ import annotations

import hashlib
import itertools
import math
import re
from typing import Protocol

import numpy as np

from .config import Settings


class Embedder(Protocol):
    name: str
    dim: int

    def embed_documents(self, texts: list[str]) -> list[np.ndarray]: ...
    def embed_query(self, text: str) -> np.ndarray: ...


class Reranker(Protocol):
    name: str

    def scores(self, query: str, documents: list[str]) -> list[float]: ...


class FastEmbedEmbedder:
    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        self.name = model_name
        self._model = TextEmbedding(model_name=model_name)
        self.dim = len(next(iter(self._model.embed(["dimension probe"]))))

    def embed_documents(self, texts: list[str]) -> list[np.ndarray]:
        return [np.asarray(v, dtype=np.float32) for v in self._model.passage_embed(texts)]

    def embed_query(self, text: str) -> np.ndarray:
        return np.asarray(next(iter(self._model.query_embed(text))), dtype=np.float32)


class FastEmbedReranker:
    """Cross-encoder: reads the query and a passage together and scores how well they match."""

    def __init__(self, model_name: str):
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self.name = model_name
        self._model = TextCrossEncoder(model_name=model_name)

    def scores(self, query: str, documents: list[str]) -> list[float]:
        return [float(s) for s in self._model.rerank(query, documents)]


_TOKEN = re.compile(r"[a-z0-9]+")


def _hash(token: str, dim: int) -> tuple[int, float]:
    digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
    value = int.from_bytes(digest, "little")
    return value % dim, 1.0 if (value >> 63) & 1 else -1.0


class HashingEmbedder:
    """Offline stand-in: bag of words and word pairs, hashed into a normalised vector."""

    name = "hashing-test-embedder"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _vector(self, text: str) -> np.ndarray:
        tokens = _TOKEN.findall(text.lower())
        features = tokens + [f"{a}_{b}" for a, b in itertools.pairwise(tokens)]
        vec = np.zeros(self.dim, dtype=np.float32)
        for feature in features:
            index, sign = _hash(feature, self.dim)
            vec[index] += sign
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm else vec

    def embed_documents(self, texts: list[str]) -> list[np.ndarray]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> np.ndarray:
        return self._vector(text)


class OverlapReranker:
    """Offline stand-in for the cross-encoder: share of query words found in the passage."""

    name = "overlap-test-reranker"

    def scores(self, query: str, documents: list[str]) -> list[float]:
        q = set(_TOKEN.findall(query.lower()))
        out = []
        for doc in documents:
            d = set(_TOKEN.findall(doc.lower()))
            out.append(len(q & d) / math.sqrt(len(q) * len(d)) if q and d else 0.0)
        return out


def load_embedder(settings: Settings) -> Embedder:
    if settings.embedder == "hashing":
        return HashingEmbedder()
    return FastEmbedEmbedder(settings.embed_model)


def load_reranker(settings: Settings) -> Reranker:
    if settings.embedder == "hashing":
        return OverlapReranker()
    return FastEmbedReranker(settings.rerank_model)
