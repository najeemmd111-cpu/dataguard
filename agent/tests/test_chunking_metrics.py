"""Pure tests: no database, no models."""

from __future__ import annotations

from pathlib import Path

import pytest

from dataguard_agent.chunking import chunk_markdown, load_docs, slugify
from dataguard_agent.evaluate import EVAL_DIR, load_questions
from dataguard_agent.metrics import hit_at_k, percentile, reciprocal_rank, unique_sections
from dataguard_agent.search import reciprocal_rank_fusion
from dataguard_agent.store import Hit

DOCS = Path(__file__).resolve().parents[2] / "docs"


def test_slugify():
    assert slugify("Step 1: read the result") == "step-1-read-the-result"
    assert slugify("orders_fresh fails") == "orders-fresh-fails"
    assert slugify("!!!") == "section"


def test_sections_split_on_level_two_headings_only():
    md = "# Page\n\nIntro text.\n\n## First\n\nA.\n\n### Detail\n\nB.\n\n## Second\n\nC.\n"
    chunks = chunk_markdown("page.md", md)
    assert [c.section_id for c in chunks] == ["page#overview", "page#first", "page#second"]
    assert "### Detail" in chunks[1].content
    assert chunks[1].text.startswith("Page: First")


def test_headings_inside_code_blocks_are_not_sections():
    md = "# Page\n\n## Real\n\n```md\n## not a heading\n```\n"
    assert [c.heading for c in chunk_markdown("p.md", md)] == ["Real"]


def test_long_sections_split_into_overlapping_parts():
    paragraphs = "\n\n".join(f"Paragraph {i} " + "word " * 60 for i in range(6))
    chunks = chunk_markdown("p.md", f"# P\n\n## Long\n\n{paragraphs}\n", max_words=150)
    assert len(chunks) > 1
    assert {c.section_id for c in chunks} == {"p#long"}
    assert [c.chunk_id for c in chunks][:2] == ["p#long~1", "p#long~2"]
    # the last paragraph of a part is repeated at the start of the next one
    assert chunks[1].content.split("\n\n")[0] == chunks[0].content.split("\n\n")[-1]


def test_duplicate_headings_get_unique_ids():
    chunks = chunk_markdown("p.md", "# P\n\n## Fix\n\nA\n\n## Fix\n\nB\n")
    assert [c.section_id for c in chunks] == ["p#fix", "p#fix-2"]


def test_real_docs_chunk_cleanly():
    chunks = load_docs(DOCS)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(c.source != "README.md" for c in chunks)
    assert len({c.source for c in chunks}) >= 20


def test_every_question_points_at_a_real_section():
    sections = {c.section_id for c in load_docs(DOCS)}
    questions = load_questions(EVAL_DIR / "questions.jsonl")
    assert len(questions) >= 50
    assert len({q.id for q in questions}) == len(questions)
    assert {q.kind for q in questions} == {"exact", "paraphrase"}
    unknown = {sid for q in questions for sid in q.relevant} - sections
    assert not unknown, f"renamed or deleted sections: {sorted(unknown)}"


def test_metrics():
    ranked = ["a", "b", "c", "d"]
    assert hit_at_k(ranked, {"c"}, 1) == 0.0
    assert hit_at_k(ranked, {"c"}, 5) == 1.0
    assert reciprocal_rank(ranked, {"c", "d"}) == pytest.approx(1 / 3)
    assert reciprocal_rank(ranked, {"z"}) == 0.0
    assert unique_sections(["a", "a", "b", "a"]) == ["a", "b"]
    assert percentile([5, 1, 3], 50) == 3


def _hit(cid: str) -> Hit:
    return Hit(cid, cid.split("~")[0], "x.md", "h", "text", 0.0)


def test_reciprocal_rank_fusion_rewards_agreement():
    keyword = [_hit("a"), _hit("b"), _hit("c")]
    vector = [_hit("c"), _hit("d"), _hit("a")]
    fused = [h.chunk_id for h in reciprocal_rank_fusion(keyword, vector)]
    # a and c appear in both lists, so they beat b and d, which appear once
    assert set(fused[:2]) == {"a", "c"}
    # a (ranks 1 and 3) and c (ranks 3 and 1) tie exactly; ties are broken by id so results are stable
    assert fused[0] == "a"
    assert set(fused[2:]) == {"b", "d"}
