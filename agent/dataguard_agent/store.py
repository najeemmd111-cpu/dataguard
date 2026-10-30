"""PostgreSQL storage for doc chunks: a tsvector for keyword search and a pgvector column for meaning search."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from .chunking import Chunk


@dataclass
class Hit:
    chunk_id: str
    section_id: str
    source: str
    heading: str
    text: str
    score: float


@contextmanager
def connect(database_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        yield conn


def rebuild(conn: psycopg.Connection, chunks: list[Chunk], vectors: list[np.ndarray], model: str) -> None:
    """Replace the whole index. The corpus is small, so a full rebuild is simplest and always consistent."""
    if len(chunks) != len(vectors):
        raise ValueError("one vector per chunk expected")
    dim = int(vectors[0].shape[0])
    with conn.transaction():
        conn.execute("CREATE SCHEMA IF NOT EXISTS dq")
        conn.execute("DROP TABLE IF EXISTS dq.doc_chunks")
        conn.execute(
            f"""
            CREATE TABLE dq.doc_chunks (
                chunk_id    TEXT PRIMARY KEY,
                section_id  TEXT NOT NULL,
                source      TEXT NOT NULL,
                title       TEXT NOT NULL,
                heading     TEXT NOT NULL,
                text        TEXT NOT NULL,
                model       TEXT NOT NULL,
                embedding   vector({dim}) NOT NULL,
                tsv         tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
                indexed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO dq.doc_chunks (chunk_id, section_id, source, title, heading, text, model, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                [(c.chunk_id, c.section_id, c.source, c.title, c.heading, c.text, model, v)
                 for c, v in zip(chunks, vectors)],
            )
        conn.execute("CREATE INDEX doc_chunks_embedding_idx ON dq.doc_chunks USING hnsw (embedding vector_cosine_ops)")
        conn.execute("CREATE INDEX doc_chunks_tsv_idx ON dq.doc_chunks USING gin (tsv)")


def indexed_model(conn: psycopg.Connection) -> str | None:
    exists = conn.execute("SELECT to_regclass('dq.doc_chunks') IS NOT NULL AS ok").fetchone()["ok"]
    if not exists:
        return None
    row = conn.execute("SELECT model FROM dq.doc_chunks LIMIT 1").fetchone()
    return row["model"] if row else None


def _hits(rows: list[dict]) -> list[Hit]:
    return [Hit(r["chunk_id"], r["section_id"], r["source"], r["heading"], r["text"], float(r["score"])) for r in rows]


def keyword_search(conn: psycopg.Connection, query: str, limit: int) -> list[Hit]:
    """PostgreSQL full-text search, ranked with ts_rank_cd.

    Words are OR-ed (any word may match) so a long natural question still finds
    passages; ranking rewards passages that match more words, closer together.
    Note: ts_rank_cd is BM25-like, not BM25.
    """
    rows = conn.execute(
        """
        WITH q AS (
            SELECT NULLIF(replace(plainto_tsquery('english', %(query)s)::text, '&', '|'), '')::tsquery AS query
        )
        SELECT chunk_id, section_id, source, heading, text, ts_rank_cd(tsv, q.query, 1) AS score
        FROM dq.doc_chunks, q
        WHERE q.query IS NOT NULL AND tsv @@ q.query
        ORDER BY score DESC, chunk_id
        LIMIT %(limit)s
        """,
        {"query": query, "limit": limit},
    ).fetchall()
    return _hits(rows)


def vector_search(conn: psycopg.Connection, query_vector: np.ndarray, limit: int) -> list[Hit]:
    """Nearest chunks by cosine distance (pgvector HNSW index); score = cosine similarity."""
    rows = conn.execute(
        """
        SELECT chunk_id, section_id, source, heading, text, 1 - (embedding <=> %(v)s) AS score
        FROM dq.doc_chunks
        ORDER BY embedding <=> %(v)s, chunk_id
        LIMIT %(limit)s
        """,
        {"v": query_vector, "limit": limit},
    ).fetchall()
    return _hits(rows)
