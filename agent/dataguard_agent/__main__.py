"""Command line.

    python -m dataguard_agent ingest                   # index docs/ into PostgreSQL
    python -m dataguard_agent search "why are orders stale?" [--method hybrid_rerank]
    python -m dataguard_agent evaluate                 # compare the four methods
    python -m dataguard_agent sections                 # list section ids (for writing questions)
"""

from __future__ import annotations

import argparse
import sys
import textwrap
import time
from pathlib import Path

from .chunking import load_docs
from .config import get_settings
from .evaluate import EVAL_DIR, build_meta, check_labels, load_questions, run, to_markdown, write_outputs
from .models import load_embedder, load_reranker
from .search import METHODS, Searcher
from .store import connect, indexed_model, rebuild


def cmd_ingest(_: argparse.Namespace) -> int:
    settings = get_settings()
    chunks = load_docs(settings.docs_dir)
    print(f"Read {len(chunks)} chunks from {len({c.source for c in chunks})} pages in {settings.docs_dir}")
    embedder = load_embedder(settings)
    start = time.perf_counter()
    vectors = embedder.embed_documents([c.text for c in chunks])
    print(f"Embedded with {embedder.name} ({embedder.dim} dimensions) in {time.perf_counter() - start:.1f}s")
    with connect(settings.database_url) as conn:
        rebuild(conn, chunks, vectors, embedder.name)
    print("Stored in dq.doc_chunks with an HNSW vector index and a full-text index.")
    return 0


def _searcher(conn, settings, need_reranker: bool) -> Searcher:
    embedder = load_embedder(settings)
    stored = indexed_model(conn)
    if stored is None:
        sys.exit("The docs are not indexed yet. Run: python -m dataguard_agent ingest")
    if stored != embedder.name:
        sys.exit(f"The index was built with {stored}, but the current model is {embedder.name}. "
                 "Run ingest again.")
    reranker = load_reranker(settings) if need_reranker else None
    return Searcher(conn, embedder, reranker, settings.candidates)


def cmd_search(args: argparse.Namespace) -> int:
    settings = get_settings()
    with connect(settings.database_url) as conn:
        searcher = _searcher(conn, settings, need_reranker=args.method == "hybrid_rerank")
        hits = searcher.search(args.query, method=args.method, limit=args.limit)
    if not hits:
        print("No matching sections.")
    for rank, hit in enumerate(hits, start=1):
        body = hit.text.split("\n\n", 1)[-1]
        print(f"{rank}. {hit.section_id}  (score {hit.score:.3f})")
        print(textwrap.indent(textwrap.shorten(body, 240, placeholder=" …"), "   "))
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    settings = get_settings()
    questions = load_questions(Path(args.questions))
    with connect(settings.database_url) as conn:
        searcher = _searcher(conn, settings, need_reranker=True)
        sections = {r["section_id"] for r in conn.execute("SELECT DISTINCT section_id FROM dq.doc_chunks")}
        counts = conn.execute("SELECT count(*) AS n, count(DISTINCT source) AS p FROM dq.doc_chunks").fetchone()
        check_labels(questions, sections)
        print(f"Evaluating {len(questions)} questions × {len(METHODS)} methods…")
        results = run(searcher, questions)
    meta = build_meta(questions, counts["n"], counts["p"], searcher.embedder.name,
                      searcher.reranker.name if searcher.reranker else "-")
    report = to_markdown(results, meta)
    print("\n" + report)
    path = write_outputs(results, meta, Path(args.output))
    print(f"Saved {path} and results.json")
    return 0


def cmd_sections(_: argparse.Namespace) -> int:
    for chunk in load_docs(get_settings().docs_dir):
        if "~" not in chunk.chunk_id or chunk.chunk_id.endswith("~1"):
            print(f"{chunk.section_id:55} {chunk.heading}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dataguard_agent", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="index docs/ into PostgreSQL").set_defaults(func=cmd_ingest)
    s = sub.add_parser("search", help="search the docs")
    s.add_argument("query")
    s.add_argument("--method", choices=METHODS, default="hybrid_rerank")
    s.add_argument("--limit", type=int, default=5)
    s.set_defaults(func=cmd_search)
    e = sub.add_parser("evaluate", help="compare the retrieval methods")
    e.add_argument("--questions", default=str(EVAL_DIR / "questions.jsonl"))
    e.add_argument("--output", default=str(EVAL_DIR))
    e.set_defaults(func=cmd_evaluate)
    sub.add_parser("sections", help="list section ids").set_defaults(func=cmd_sections)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
