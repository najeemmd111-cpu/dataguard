"""Command line.

    python -m dataguard_agent ingest                   # index docs/ into PostgreSQL
    python -m dataguard_agent search "why are orders stale?" [--method hybrid_rerank]
    python -m dataguard_agent evaluate                 # compare the four methods
    python -m dataguard_agent sections                 # list section ids (for writing questions)

    python -m dataguard_agent setup                    # agent tables + read-only database user
    python -m dataguard_agent investigate orders_fresh # explain why a rule failed (needs Ollama)
    python -m dataguard_agent evaluate-agent           # grade the agent on failures with a known cause
    python -m dataguard_agent regrade 2 3 4 5          # re-grade saved investigations (e.g. after changing the grader)
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import time
from pathlib import Path

from .agent import AgentError, RootCauseAgent, find_dataset
from .agent_eval import grade, load_cases
from .agent_eval import to_markdown as agent_markdown
from .chunking import load_docs
from .config import get_settings
from .db_setup import setup
from .evaluate import EVAL_DIR, build_meta, check_labels, load_questions, run, to_markdown, write_outputs
from .llm import LLMError, LoggedLLM, make_backend
from .models import load_embedder, load_reranker
from .search import METHODS, Searcher
from .store import connect, indexed_model, rebuild
from .tools import Tools


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


def cmd_setup(_: argparse.Namespace) -> int:
    settings = get_settings()
    with connect(settings.database_url) as conn:
        setup(conn, settings)
    print(f"Ready: dq.investigations, dq.llm_calls, and the read-only user {settings.readonly_user}.")
    return 0


def _agent(conn, settings) -> RootCauseAgent:
    setup(conn, settings)
    searcher = _searcher(conn, settings, need_reranker=True)
    llm = LoggedLLM(make_backend(settings), conn, settings)
    return RootCauseAgent(conn, llm, Tools(conn, searcher, settings), settings)


def print_record(record: dict, verbose: bool) -> None:
    head = f"{record['dataset']}/{record['rule_id']}"
    if record["status"] != "ok":
        print(f"Investigation of {head} failed: {record['error']}")
        return
    a = record["answer"]
    print(f"\n{head}  (confidence: {a['confidence']})\n")
    print(textwrap.fill(a["summary"], 100))
    print("\nLikely cause\n" + textwrap.indent(textwrap.fill(a["likely_cause"], 96), "  "))
    print("\nEvidence")
    for e in a["evidence"]:
        print("  - " + e)
    print("\nFix")
    for i, step in enumerate(a["fix_steps"], 1):
        print(f"  {i}. {step}")
    print("\nSources: " + (", ".join(a["sources"]) or "none verified"))
    if verbose:
        print("\nTrace")
        for t in record["trace"]:
            if t["type"] == "tool":
                print(f"  round {t['round']}: {t['tool']}({json.dumps(t['arguments'])}) -> {t['result'][:120]}")
            else:
                print(f"  {t['type']}: {json.dumps({k: v for k, v in t.items() if k != 'type'}, default=str)[:160]}")
    print(f"\n{record['tool_calls']} tool call(s), {record['input_tokens'] + record['output_tokens']:,} tokens, "
          f"{record['latency_ms'] / 1000:.1f} s, model {record['model']}. Saved as investigation "
          f"{record['investigation_id']}.")


def cmd_investigate(args: argparse.Namespace) -> int:
    settings = get_settings()
    with connect(settings.database_url) as conn:
        try:
            dataset = args.dataset or find_dataset(conn, args.rule_id)
            agent = _agent(conn, settings)
            print(f"Investigating {dataset}/{args.rule_id} with {agent.llm.model}… (a local model can take a minute)")
            record = agent.investigate(dataset, args.rule_id, args.result_id)
        except (AgentError, LLMError) as exc:
            print(f"Error: {exc}")
            return 1
    print_record(record, args.verbose)
    return 0 if record["status"] == "ok" else 1


def cmd_evaluate_agent(args: argparse.Namespace) -> int:
    settings = get_settings()
    cases = load_cases(Path(args.cases))
    rows = []
    with connect(settings.database_url) as conn:
        agent = _agent(conn, settings)
        for case in cases:
            for run in range(1, args.repeat + 1):
                label = f" (run {run}/{args.repeat})" if args.repeat > 1 else ""
                print(f"Investigating {case.dataset}/{case.rule_id}{label}…", flush=True)
                agent.llm.total_in = agent.llm.total_out = 0
                agent.tools.seen_sections.clear()
                try:
                    record = agent.investigate(case.dataset, case.rule_id)
                except AgentError as exc:
                    print(f"  skipped: {exc}")
                    break
                rows.append(grade(case, record))
    report = agent_markdown(rows, settings.llm_model)
    print("\n" + report)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "agent_results.md").write_text(report, encoding="utf-8")
    (out / "agent_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Saved {out / 'agent_results.md'}")
    return 0


def cmd_regrade(args: argparse.Namespace) -> int:
    settings = get_settings()
    cases = {(c.dataset, c.rule_id): c for c in load_cases(Path(args.cases))}
    rows, models = [], set()
    with connect(settings.database_url) as conn:
        for inv_id in args.ids:
            record = conn.execute("SELECT * FROM dq.investigations WHERE investigation_id = %s", (inv_id,)).fetchone()
            if not record:
                print(f"Investigation {inv_id} not found, skipped.")
                continue
            case = cases.get((record["dataset"], record["rule_id"]))
            if not case:
                print(f"Investigation {inv_id} ({record['rule_id']}) has no test case, skipped.")
                continue
            models.add(record["model"])
            rows.append(grade(case, record))
    if not rows:
        print("Nothing to grade.")
        return 1
    report = agent_markdown(rows, ", ".join(sorted(models)), title=args.title)
    print("\n" + report)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.name}.md").write_text(report, encoding="utf-8")
    print(f"Saved {out / (args.name + '.md')}")
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
    sub.add_parser("setup", help="create agent tables and the read-only user").set_defaults(func=cmd_setup)
    i = sub.add_parser("investigate", help="explain why a rule failed")
    i.add_argument("rule_id")
    i.add_argument("--dataset", help="defaults to the dataset the rule belongs to")
    i.add_argument("--result-id", type=int, help="explain a specific result instead of the latest")
    i.add_argument("-v", "--verbose", action="store_true", help="show every tool call")
    i.set_defaults(func=cmd_investigate)
    a = sub.add_parser("evaluate-agent", help="grade the agent on failures with a known cause")
    a.add_argument("--cases", default=str(EVAL_DIR / "agent_cases.jsonl"))
    a.add_argument("--output", default=str(EVAL_DIR))
    a.add_argument("--repeat", type=int, default=1,
                   help="run each case N times to measure consistency (answers vary between runs)")
    a.set_defaults(func=cmd_evaluate_agent)
    r = sub.add_parser("regrade", help="re-grade saved investigations by id")
    r.add_argument("ids", nargs="+", type=int)
    r.add_argument("--cases", default=str(EVAL_DIR / "agent_cases.jsonl"))
    r.add_argument("--output", default=str(EVAL_DIR))
    r.add_argument("--name", default="agent_results_before", help="output file name, without .md")
    r.add_argument("--title", default="Root-cause agent evaluation (re-graded)")
    r.set_defaults(func=cmd_regrade)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
