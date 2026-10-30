"""Database tests: real PostgreSQL + pgvector, offline stand-in models (no downloads)."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

from dataguard_agent.chunking import load_docs
from dataguard_agent.evaluate import EVAL_DIR, load_questions, run
from dataguard_agent.models import HashingEmbedder, OverlapReranker
from dataguard_agent.search import METHODS, Searcher
from dataguard_agent.store import connect, indexed_model, rebuild

DOCS = Path(__file__).resolve().parents[2] / "docs"
DB_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not DB_URL, reason="set TEST_DATABASE_URL to a PostgreSQL with pgvector")


@pytest.fixture(scope="module")
def searcher():
    try:
        with connect(DB_URL) as conn:
            embedder = HashingEmbedder()
            chunks = load_docs(DOCS)
            rebuild(conn, chunks, embedder.embed_documents([c.text for c in chunks]), embedder.name)
            yield Searcher(conn, embedder, OverlapReranker(), candidates=20)
    except psycopg.errors.FeatureNotSupported as exc:  # pragma: no cover
        pytest.skip(f"pgvector missing: {exc}")


def test_index_is_built(searcher):
    conn = searcher.conn
    assert indexed_model(conn) == "hashing-test-embedder"
    n = conn.execute("SELECT count(*) AS n FROM dq.doc_chunks").fetchone()["n"]
    assert n == len(load_docs(DOCS))
    indexes = {r["indexname"] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'doc_chunks'")}
    assert {"doc_chunks_embedding_idx", "doc_chunks_tsv_idx"} <= indexes


def test_keyword_search_finds_rule_ids(searcher):
    hits = searcher.search("orders_unique_id fails", method="keyword", limit=3)
    assert hits[0].section_id == "runbook-orders#orders-unique-id-fails"
    assert hits == sorted(hits, key=lambda h: -h.score)


def test_keyword_search_handles_empty_and_stop_word_queries(searcher):
    assert searcher.search("the of and", method="keyword") == []
    assert searcher.search("", method="keyword") == []


@pytest.mark.parametrize("method", METHODS)
def test_every_method_returns_ranked_results(searcher, method):
    hits = searcher.search("how do I stop duplicate loads", method=method, limit=5)
    assert 0 < len(hits) <= 5
    assert len({h.chunk_id for h in hits}) == len(hits)
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


def test_unknown_method_is_rejected(searcher):
    with pytest.raises(ValueError, match="unknown method"):
        searcher.search("x", method="magic")


def test_rebuild_replaces_the_index_and_changes_dimension(searcher):
    conn = searcher.conn
    small = HashingEmbedder(dim=64)
    chunks = load_docs(DOCS)[:5]
    rebuild(conn, chunks, small.embed_documents([c.text for c in chunks]), "other-model")
    assert conn.execute("SELECT count(*) AS n FROM dq.doc_chunks").fetchone()["n"] == 5
    assert indexed_model(conn) == "other-model"
    # restore the full index for any later tests
    full = load_docs(DOCS)
    rebuild(conn, full, searcher.embedder.embed_documents([c.text for c in full]), searcher.embedder.name)


def test_evaluation_runs_end_to_end(searcher):
    questions = load_questions(EVAL_DIR / "questions.jsonl")[:10]
    results = run(searcher, questions)
    assert [r.method for r in results] == list(METHODS)
    for r in results:
        s = r.summary()
        assert 0 <= s["hit_at_1"] <= s["recall_at_5"] <= 1
        assert len(r.latency_ms) == 10
