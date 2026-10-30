"""Retrieval metrics, computed per question on the ranked list of *sections* returned."""

from __future__ import annotations

from collections.abc import Sequence


def unique_sections(section_ids: Sequence[str]) -> list[str]:
    """A long section may be split into parts; count each section once, at its best rank."""
    seen: set[str] = set()
    out = []
    for sid in section_ids:
        if sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def first_relevant_rank(ranked: Sequence[str], relevant: set[str]) -> int | None:
    for rank, sid in enumerate(ranked, start=1):
        if sid in relevant:
            return rank
    return None


def hit_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """1.0 if any relevant section is in the top k, else 0.0 (often called recall@k for single-answer sets)."""
    rank = first_relevant_rank(ranked, relevant)
    return 1.0 if rank is not None and rank <= k else 0.0


def reciprocal_rank(ranked: Sequence[str], relevant: set[str]) -> float:
    rank = first_relevant_rank(ranked, relevant)
    return 1.0 / rank if rank else 0.0


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(p / 100 * (len(ordered) - 1))))
    return ordered[index]
