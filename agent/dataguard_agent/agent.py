"""Root-cause agent: explain why a data-quality rule failed.

1. Gather: the failure (measured value, threshold, sample rows) and the docs most
   related to it are collected by code, so even a small model starts well informed.
2. Investigate: the model may call tools (search_docs, rule_history, run_sql) for
   a few rounds to check its ideas against the data.
3. Answer: the model writes a structured answer (JSON schema enforced by Ollama),
   which is validated. Cited sources must be sections it was actually shown.

Every model call is logged in dq.llm_calls; every investigation, with its full
trace, in dq.investigations.
"""

from __future__ import annotations

import json
import re
import time
from typing import Literal

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, ValidationError

from .config import Settings
from .llm import LLMError, LoggedLLM
from .tools import TABLES_HELP, TOOL_SPECS, Tools


class Answer(BaseModel):
    summary: str = Field(description="One sentence a busy engineer can read")
    likely_cause: str
    evidence: list[str] = Field(description="Facts observed in the failure details or tool results, with numbers")
    fix_steps: list[str]
    confidence: Literal["low", "medium", "high"]
    sources: list[str] = Field(description="Section ids from the documentation that support the answer")


class AgentError(Exception):
    pass


SYSTEM_PROMPT = """You are DataGuard's root-cause assistant. A data-quality rule has failed. \
Find the most likely cause and how to fix it.

You can call tools:
- search_docs: the team's documentation of causes, runbooks and fixes
- rule_history: when this rule started failing
- run_sql: one read-only SELECT to check the data. Tables: {tables}

Rules:
- You can only READ data. You cannot change, delete, fix or re-run anything. Never claim you did.
- Only the tables listed above exist. There is no table of jobs, schedules or logs.
- Base every statement on the failure details, tool results or documentation. Never invent numbers or events.
- Be efficient: at most {rounds} rounds of tool calls. Stop calling tools once you have enough evidence.
- Cite documentation by its section id in square brackets, for example [runbook-orders#orders-fresh-fails]."""

FINAL_PROMPT = """Now write your final answer as JSON with these fields:
- summary: one sentence
- likely_cause: the most likely cause, consistent with the documentation you found
- evidence: facts you actually observed, each quoting a number or value from the failure details or a tool \
result (for example "measured 193.9h against 24h allowed"). Do not include anything a tool result did not show.
- fix_steps: concrete actions for a person to take. You have not done any of them.
- confidence: low, medium or high. Use low if your tool calls failed or the evidence is thin.
- sources: the section ids of the documentation you relied on, exactly as written in square brackets."""

# The agent can only read. Wording like this in the summary, cause or evidence is a false claim.
ACTION_CLAIM = re.compile(
    r"\b(i|we) (deleted|removed|fixed|updated|restarted|reran|re-ran|dropped)\b"
    r"|\b(was|were|has been|have been|got) (deleted|removed|fixed|dropped|restarted|corrected)\b"
    r"|\b(deleted|deleting|removed|removing|dropped|dropping) \d[\d,]* (rows|records|orders|duplicates|duplicate)"
    r"|executed successfully"
    # "the rule has been updated", "the threshold was raised": the agent cannot change rules either
    r"|\b(rule|rules|threshold|thresholds|contract|min_ratio|max_age)\b[^.]{0,60}?"
    r"\b(has been|have been|was|were|is now|got) (updated|adjusted|changed|raised|lowered|increased|decreased|relaxed)\b",
    re.IGNORECASE,
)


def claimed_actions(answer: dict) -> list[str]:
    text = " ".join([answer.get("summary", ""), answer.get("likely_cause", ""), *answer.get("evidence", [])])
    return sorted({m.group(0) for m in ACTION_CLAIM.finditer(text)})


def latest_result(conn: psycopg.Connection, dataset: str, rule_id: str, result_id: int | None = None) -> dict:
    if result_id is not None:
        row = conn.execute("SELECT * FROM dq.results WHERE result_id = %s", (result_id,)).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM dq.results WHERE dataset = %s AND rule_id = %s "
            "ORDER BY checked_at DESC, result_id DESC LIMIT 1",
            (dataset, rule_id),
        ).fetchone()
    if not row:
        raise AgentError(f"No check results for {dataset}/{rule_id}. Run the checks first.")
    return row


def find_dataset(conn: psycopg.Connection, rule_id: str) -> str:
    row = conn.execute(
        "SELECT dataset FROM dq.results WHERE rule_id = %s ORDER BY checked_at DESC LIMIT 1", (rule_id,)
    ).fetchone()
    if not row:
        raise AgentError(f"Unknown rule {rule_id!r}: it has no check results.")
    return row["dataset"]


def failure_context(result: dict) -> dict:
    return {
        "dataset": result["dataset"],
        "rule_id": result["rule_id"],
        "rule_type": result["rule_type"],
        "severity": result["severity"],
        "passed": result["passed"],
        "measured_value": result["measured_value"],
        "allowed": result["threshold"],
        "message": result["message"],
        "checked_at": str(result["checked_at"]),
        "sample_rows": result["sample_rows"][:5],
    }


class RootCauseAgent:
    def __init__(self, conn: psycopg.Connection, llm: LoggedLLM, tools: Tools, settings: Settings):
        self.conn = conn
        self.llm = llm
        self.tools = tools
        self.settings = settings

    def investigate(self, dataset: str, rule_id: str, result_id: int | None = None) -> dict:
        result = latest_result(self.conn, dataset, rule_id, result_id)
        inv_id = self.conn.execute(
            "INSERT INTO dq.investigations (dataset, rule_id, result_id, model) VALUES (%s, %s, %s, %s) "
            "RETURNING investigation_id",
            (dataset, rule_id, result["result_id"], self.llm.model),
        ).fetchone()["investigation_id"]
        self.conn.commit()
        self.llm.investigation_id = inv_id
        start = time.perf_counter()
        trace: list[dict] = []
        try:
            answer = self._run(result, trace)
            status, error = "ok", None
        except (LLMError, AgentError) as exc:
            answer, status, error = None, "error", str(exc)
        record = {
            "investigation_id": inv_id,
            "dataset": dataset,
            "rule_id": rule_id,
            "result_id": result["result_id"],
            "model": self.llm.model,
            "status": status,
            "answer": answer,
            "error": error,
            "trace": trace,
            "tool_calls": sum(1 for t in trace if t["type"] == "tool"),
            "input_tokens": self.llm.total_in,
            "output_tokens": self.llm.total_out,
            "latency_ms": round((time.perf_counter() - start) * 1000),
        }
        self.conn.execute(
            "UPDATE dq.investigations SET status = %s, answer = %s, trace = %s, tool_calls = %s, "
            "input_tokens = %s, output_tokens = %s, latency_ms = %s, error = %s WHERE investigation_id = %s",
            (status, Jsonb(answer) if answer else None, Jsonb(trace), record["tool_calls"],
             record["input_tokens"], record["output_tokens"], record["latency_ms"], error, inv_id),
        )
        self.conn.commit()
        return record

    def _run(self, result: dict, trace: list[dict]) -> dict:
        context = failure_context(result)
        if context["passed"]:
            trace.append({"type": "note", "text": "The latest result passes; explaining the last check anyway."})

        # 1. Gather: retrieve docs for this kind of failure before the model starts.
        query = f"{context['rule_type']} rule {context['rule_id']} fails: {context['message']}"
        docs = self.tools.search_docs(query, limit=4)
        trace.append({"type": "retrieval", "query": query, "sections": list(self.tools.seen_sections)})

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(tables=TABLES_HELP,
                                                               rounds=self.settings.max_tool_rounds)},
            {"role": "user", "content": (
                f"Rule `{context['rule_id']}` on dataset `{context['dataset']}` failed.\n\n"
                f"Key facts: measured {context['measured_value']}, allowed {context['allowed']}. "
                f"{context['message']}\n\n"
                f"Failure details:\n{json.dumps(context, default=str, indent=1)}\n\n"
                f"Documentation found for this failure:\n{docs}\n\n"
                "Investigate with the tools if needed, then stop."
            )},
        ]

        # 2. Investigate: a few rounds of tool calls.
        for round_no in range(1, self.settings.max_tool_rounds + 1):
            reply = self.llm.chat(messages, purpose="agent-step", tools=TOOL_SPECS)
            if not reply.tool_calls:
                if reply.content.strip():
                    trace.append({"type": "thought", "round": round_no, "text": reply.content.strip()[:1000]})
                break
            messages.append({"role": "assistant", "content": reply.content,
                             "tool_calls": [{"function": {"name": c.name, "arguments": c.arguments}}
                                            for c in reply.tool_calls]})
            for call in reply.tool_calls:
                t0 = time.perf_counter()
                output = self.tools.call(call.name, call.arguments)
                trace.append({"type": "tool", "round": round_no, "tool": call.name, "arguments": call.arguments,
                              "result": output[:600], "ms": round((time.perf_counter() - t0) * 1000)})
                messages.append({"role": "tool", "tool_name": call.name, "content": output})

        # 3. Answer: structured output, validated; one retry if the JSON does not fit.
        messages.append({"role": "user", "content": FINAL_PROMPT})
        schema = Answer.model_json_schema()
        for attempt in (1, 2):
            reply = self.llm.chat(messages, purpose="agent-answer", schema=schema)
            try:
                answer = Answer.model_validate_json(reply.content)
                break
            except ValidationError as exc:
                trace.append({"type": "invalid_answer", "attempt": attempt, "error": str(exc)[:500]})
                if attempt == 2:
                    raise AgentError("The model did not produce a valid answer after two attempts.") from exc
                messages.append({"role": "assistant", "content": reply.content})
                messages.append({"role": "user", "content": f"That was not valid. Fix it and answer with JSON "
                                                            f"only. Problem: {str(exc)[:300]}"})

        # Keep only sources the model was actually shown; record any it made up.
        cited = [s.strip("[] ") for s in answer.sources]
        verified = [s for s in cited if s in self.tools.seen_sections]
        unverified = [s for s in cited if s not in self.tools.seen_sections]
        if unverified:
            trace.append({"type": "unverified_sources", "sources": unverified})
        out = answer.model_dump()
        out["sources"] = list(dict.fromkeys(verified))

        # Guard: the agent cannot change data, so an answer claiming it did is wrong. Say so loudly.
        claims = claimed_actions(out)
        out["warnings"] = []
        if claims:
            out["warnings"].append(
                "This answer claims an action the agent cannot take (it can only read data): "
                + "; ".join(f'"{c}"' for c in claims) + ". Treat it with caution."
            )
            out["confidence"] = "low"
            trace.append({"type": "false_action_claim", "claims": claims})
        if not out["sources"]:
            out["warnings"].append("No documentation source could be verified for this answer.")
        return out
