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

from .agent import claimed_actions
from .metrics import mean, percentile


@dataclass
class Case:
    dataset: str
    rule_id: str
    sources: list[str]              # acceptable section ids or page prefixes ending in "#"
    must_mention: list[list[str]]   # key facts, anywhere in the answer
    cause: list[list[str]]          # what the summary + likely cause must say
    wrong: list[str]                # known wrong conclusions (any of these in summary/cause/evidence fails)


def load_cases(path: Path) -> list[Case]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            cases.append(Case(d["dataset"], d["rule_id"], d["sources"], d["must_mention"],
                              d.get("cause", []), d.get("wrong", [])))
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
    cause_text = " ".join([answer.get("summary", ""), answer.get("likely_cause", "")]).lower()
    claims_text = " ".join([cause_text, *answer.get("evidence", [])]).lower()
    false_claims = claimed_actions(answer) + [w for w in case.wrong if w.lower() in claims_text]
    ok = record["status"] == "ok"
    right_cause = ok and all(any(w.lower() in cause_text for w in g) for g in case.cause)
    cites = _source_ok(answer.get("sources", []), case.sources)
    return {
        "investigation_id": record.get("investigation_id"),
        "rule": f"{case.dataset}/{case.rule_id}",
        "ok": ok,
        "right_cause": right_cause,
        "false_claims": false_claims,
        "correct": ok and right_cause and cites and not false_claims,
        "cites_right_doc": cites,
        "key_facts": sum(groups_hit) / len(groups_hit) if groups_hit else 1.0,
        "missing_facts": [case.must_mention[i] for i, hit in enumerate(groups_hit) if not hit],
        "tool_calls": record["tool_calls"],
        "tokens": record["input_tokens"] + record["output_tokens"],
        "latency_s": record["latency_ms"] / 1000,
        "summary": answer.get("summary", record.get("error") or ""),
    }


def _yes(v: bool) -> str:
    return "yes" if v else "**no**"


def to_markdown(rows: list[dict], model: str, title: str = "Root-cause agent evaluation") -> str:
    lines = [
        f"# {title}",
        "",
        f"Model: `{model}` (local, via Ollama). {len(rows)} failures with a known cause.",
        "",
        ("| Failure | Correct | Right cause | No false claims | Cites a right doc | Key facts | Tool calls "
        "| Tokens | Time |"),
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['rule']}` | {_yes(r['correct'])} | {_yes(r['right_cause'])} | {_yes(not r['false_claims'])} "
            f"| {_yes(r['cites_right_doc'])} | {r['key_facts']:.0%} | {r['tool_calls']} | {r['tokens']:,} "
            f"| {r['latency_s']:.1f} s |"
        )
    lat = [r["latency_s"] for r in rows]
    lines += [
        (f"| **Overall** | **{mean([r['correct'] for r in rows]):.0%}** | {mean([r['right_cause'] for r in rows]):.0%} "
         f"| {mean([not r['false_claims'] for r in rows]):.0%} | {mean([r['cites_right_doc'] for r in rows]):.0%} "
         f"| {mean([r['key_facts'] for r in rows]):.0%} | {mean([r['tool_calls'] for r in rows]):.1f} avg "
         f"| {mean([r['tokens'] for r in rows]):,.0f} avg | {percentile(lat, 50):.1f} s median |"),
        "",
        "- **Correct**: valid answer with the right cause, a right source, and no false claims.",
        "- **Right cause**: the summary and likely cause name the real cause (for example a stopped ETL job).",
        ("- **No false claims**: does not claim to have changed data (the agent can only read) and does not state "
        "a known wrong conclusion."),
        "- **Cites a right doc**: at least one cited section explains this failure.",
        "- **Key facts**: share of expected facts mentioned anywhere (for example *duplicate* and *upsert*).",
        "",
        "Grading uses keywords, not a second model: transparent, but it does not judge reasoning quality.",
        "",
        "## Answers",
        "",
    ]
    for r in rows:
        lines.append(f"- `{r['rule']}` (investigation {r.get('investigation_id')}): {r['summary']}")
        if r["false_claims"]:
            lines.append(f"  - False claims: {', '.join(r['false_claims'])}")
        if r["missing_facts"]:
            lines.append(f"  - Missing: {', '.join('/'.join(g) for g in r['missing_facts'])}")
    lines.append("")
    return "\n".join(lines)
