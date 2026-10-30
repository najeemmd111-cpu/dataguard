"""Score the four retrieval methods on the question set in eval/questions.jsonl."""

from __future__ import annotations

import json
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .metrics import hit_at_k, mean, percentile, reciprocal_rank, unique_sections
from .search import METHODS, Searcher

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"

LABELS = {
    "keyword": "Keyword (PostgreSQL full-text)",
    "vector": "Vector (pgvector embeddings)",
    "hybrid": "Hybrid (RRF of both)",
    "hybrid_rerank": "Hybrid + cross-encoder re-rank",
}


@dataclass
class Question:
    id: str
    question: str
    relevant: list[str]
    kind: str


@dataclass
class MethodResult:
    method: str
    hit1: list[float] = field(default_factory=list)
    hit5: list[float] = field(default_factory=list)
    rr: list[float] = field(default_factory=list)
    latency_ms: list[float] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)
    misses: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        by_kind: dict[str, list[float]] = {}
        for kind, h in zip(self.kinds, self.hit5):
            by_kind.setdefault(kind, []).append(h)
        return {
            "method": self.method,
            "hit_at_1": round(mean(self.hit1), 3),
            "recall_at_5": round(mean(self.hit5), 3),
            "mrr_at_10": round(mean(self.rr), 3),
            "recall_at_5_by_kind": {k: round(mean(v), 3) for k, v in sorted(by_kind.items())},
            "latency_ms_median": round(percentile(self.latency_ms, 50), 1),
            "latency_ms_p95": round(percentile(self.latency_ms, 95), 1),
        }


def load_questions(path: Path) -> list[Question]:
    questions = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            data = json.loads(line)
            try:
                questions.append(Question(data["id"], data["question"], data["relevant"], data["kind"]))
            except KeyError as exc:
                raise ValueError(f"{path.name} line {n}: missing field {exc}") from exc
    return questions


def check_labels(questions: list[Question], known_sections: set[str]) -> None:
    unknown = sorted({sid for q in questions for sid in q.relevant} - known_sections)
    if unknown:
        raise ValueError(
            "These sections in the question set do not exist in the index "
            f"(renamed heading or page?): {', '.join(unknown)}"
        )


def run(searcher: Searcher, questions: list[Question], methods: tuple[str, ...] = METHODS) -> list[MethodResult]:
    # Warm-up: the first call loads the ONNX models; it should not count as query latency.
    for method in methods:
        searcher.search("warm up", method=method, limit=5)

    results = []
    for method in methods:
        res = MethodResult(method)
        for q in questions:
            relevant = set(q.relevant)
            start = time.perf_counter()
            hits = searcher.search(q.question, method=method, limit=15)
            res.latency_ms.append((time.perf_counter() - start) * 1000)
            ranked = unique_sections([h.section_id for h in hits])[:10]
            res.hit1.append(hit_at_k(ranked, relevant, 1))
            res.hit5.append(hit_at_k(ranked, relevant, 5))
            res.rr.append(reciprocal_rank(ranked, relevant))
            res.kinds.append(q.kind)
            if not hit_at_k(ranked, relevant, 5):
                res.misses.append({"id": q.id, "question": q.question, "expected": q.relevant, "got": ranked[:3]})
        results.append(res)
    return results


def to_markdown(results: list[MethodResult], meta: dict) -> str:
    kinds = sorted({k for r in results for k in r.kinds})
    lines = [
        "# Retrieval evaluation",
        "",
        (f"{meta['questions']} questions over {meta['chunks']} chunks from {meta['pages']} pages. "
        f"Embeddings: `{meta['embed_model']}`. Re-ranker: `{meta['rerank_model']}`. "
        f"Run {meta['date']} on {meta['machine']}."),
        "",
    ]
    if meta.get("test_models"):
        lines += [
            ("> **Not real results.** This run used the offline test stand-ins instead of the real models "
            "(DG_EMBEDDER=hashing). Run without it to measure the real embedding model and re-ranker."),
            "",
        ]
    lines += [
        "| Method | Hit@1 | Recall@5 | MRR@10 | " + " | ".join(f"Recall@5 ({k})" for k in kinds)
        + " | Median latency | p95 latency |",
        "|---|---|---|---|" + "---|" * len(kinds) + "---|---|",
    ]
    for r in results:
        s = r.summary()
        by_kind = " | ".join(f"{s['recall_at_5_by_kind'].get(k, 0):.2f}" for k in kinds)
        lines.append(
            f"| {LABELS.get(r.method, r.method)} | {s['hit_at_1']:.2f} | **{s['recall_at_5']:.2f}** | "
            f"{s['mrr_at_10']:.2f} | {by_kind} | {s['latency_ms_median']:.0f} ms | {s['latency_ms_p95']:.0f} ms |"
        )
    lines += [
        "",
        "- **Hit@1**: share of questions whose answer section is ranked first.",
        "- **Recall@5**: share of questions whose answer section is in the top 5.",
        "- **MRR@10**: mean of 1 / rank of the answer section (0 if not in the top 10).",
        ("- **exact** questions reuse words from the docs (rule ids, settings); "
        "**paraphrase** questions describe the problem in other words."),
        "",
    ]
    best = max(results, key=lambda r: (mean(r.hit5), mean(r.rr)))
    if best.misses:
        lines += [f"## Questions {LABELS.get(best.method, best.method)} missed (not in the top 5)", ""]
        for m in best.misses:
            lines.append(f"- `{m['id']}` {m['question']} — expected `{', '.join(m['expected'])}`, "
                         f"top 3: `{', '.join(m['got'])}`")
        lines.append("")
    return "\n".join(lines)


def write_outputs(results: list[MethodResult], meta: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "results.md"
    md_path.write_text(to_markdown(results, meta), encoding="utf-8")
    (out_dir / "results.json").write_text(
        json.dumps({"meta": meta, "methods": [r.summary() for r in results],
                    "misses": {r.method: r.misses for r in results}}, indent=2),
        encoding="utf-8",
    )
    return md_path


def build_meta(questions: list[Question], chunks: int, pages: int, embed_model: str, rerank_model: str) -> dict:
    return {
        "questions": len(questions),
        "chunks": chunks,
        "pages": pages,
        "embed_model": embed_model,
        "rerank_model": rerank_model,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "machine": f"{platform.system()} {platform.machine()}",
        "test_models": embed_model.endswith("-test-embedder"),
    }
