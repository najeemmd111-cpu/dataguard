"""Grade the agent's answers on failures whose cause is known.

The seed data injects four problems on purpose, so the right explanation is known.
Each case lists documentation sections a correct answer should cite (any one is
enough) and groups of key words: a group is satisfied when the answer mentions any
word in it. Grading is deliberately simple and transparent: no second model judges
the first.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .metrics import mean, percentile


@dataclass
class Case:
    dataset: str
    rule_id: str
    sources: list[str]          # acceptable section ids or page prefixes ending in "#"
    must_mention: list[list[str]]


def load_cases(path: Path) -> list[Case]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            cases.append(Case(d["dataset"], d["rule_id"], d["sources"], d["must_mention"]))
    return cases


def _source_ok(cited: list[str], accepted: list[str]) -> bool:
    return any(c == a or (a.endswith("#") and c.startswith(a)) for c in cited for a in accepted)


def grade(case: Case, record: dict) -> dict:
    answer = record.get("answer") or {}
    text = " ".join(
        [answer.get("summary", ""), answer.get("likely_cause", "")]
        + answer.get("evidence", []) + answer.get("fix_steps", [])
    ).lower()
    groups_hit = [any(word.lower() in text for word in group) for group in case.must_mention]
    return {
        "rule": f"{case.dataset}/{case.rule_id}",
        "ok": record["status"] == "ok",
        "cites_right_doc": _source_ok(answer.get("sources", []), case.sources),
        "key_facts": sum(groups_hit) / len(groups_hit) if groups_hit else 1.0,
        "missing_facts": [case.must_mention[i] for i, hit in enumerate(groups_hit) if not hit],
        "tool_calls": record["tool_calls"],
        "tokens": record["input_tokens"] + record["output_tokens"],
        "latency_s": record["latency_ms"] / 1000,
        "summary": answer.get("summary", record.get("error") or ""),
    }


def to_markdown(rows: list[dict], model: str) -> str:
    lines = [
        "# Root-cause agent evaluation",
        "",
        f"Model: `{model}` (local, via Ollama). {len(rows)} failures with a known cause.",
        "",
        "| Failure | Valid answer | Cites a right doc | Key facts | Tool calls | Tokens | Time |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['rule']}` | {'yes' if r['ok'] else 'no'} | {'yes' if r['cites_right_doc'] else 'no'} | "
            f"{r['key_facts']:.0%} | {r['tool_calls']} | {r['tokens']:,} | {r['latency_s']:.1f} s |"
        )
    lat = [r["latency_s"] for r in rows]
    lines += [
        (f"| **Overall** | {mean([r['ok'] for r in rows]):.0%} | {mean([r['cites_right_doc'] for r in rows]):.0%} | "
        f"{mean([r['key_facts'] for r in rows]):.0%} | {mean([r['tool_calls'] for r in rows]):.1f} avg | "
        f"{mean([r['tokens'] for r in rows]):,.0f} avg | {percentile(lat, 50):.1f} s median |"),
        "",
        "- **Valid answer**: the model produced JSON matching the answer schema.",
        "- **Cites a right doc**: at least one cited section is one that explains this failure.",
        "- **Key facts**: share of expected facts the answer mentions (for example *duplicate* and *upsert*).",
        "",
        "## Answers",
        "",
    ]
    for r in rows:
        lines.append(f"- `{r['rule']}`: {r['summary']}")
        if r["missing_facts"]:
            lines.append(f"  - Missing: {', '.join('/'.join(g) for g in r['missing_facts'])}")
    lines.append("")
    return "\n".join(lines)
