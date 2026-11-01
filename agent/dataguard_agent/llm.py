"""Language model client. Every call is logged to dq.llm_calls with tokens, cost and latency.

The default backend is Ollama running on your own machine (free). The scripted
backend replays prepared answers, so the agent can be tested without a model.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import psycopg

from .config import Settings


class LLMError(Exception):
    """A model call failed in a way the user can fix (Ollama not running, model not pulled…)."""


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class Reply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class Backend(Protocol):
    model: str

    def chat(self, messages: list[dict], tools: list[dict] | None, schema: dict | None) -> Reply: ...


class OllamaBackend:
    def __init__(self, url: str, model: str):
        from ollama import Client

        self.url = url
        self.model = model
        self._client = Client(host=url, timeout=300)

    def chat(self, messages: list[dict], tools: list[dict] | None, schema: dict | None) -> Reply:
        from ollama import ResponseError

        start = time.perf_counter()
        try:
            response = self._client.chat(
                model=self.model,
                messages=messages,
                tools=tools or None,
                format=schema,
                # temperature 0: repeatable answers; num_ctx: Ollama's default 2048 tokens is too small here
                options={"temperature": 0, "num_ctx": 8192},
            )
        except ResponseError as exc:
            if exc.status_code == 404:
                raise LLMError(f"The model {self.model} is not downloaded. Run: ollama pull {self.model}") from exc
            raise LLMError(f"Ollama returned an error: {exc.error}") from exc
        except Exception as exc:  # connection refused, timeout…
            raise LLMError(
                f"Cannot reach Ollama at {self.url} ({exc.__class__.__name__}). "
                "Is the Ollama app running? Check with: ollama list"
            ) from exc
        message = response.message
        calls = [ToolCall(c.function.name, dict(c.function.arguments or {})) for c in (message.tool_calls or [])]
        return Reply(
            content=message.content or "",
            tool_calls=calls,
            input_tokens=response.prompt_eval_count or 0,
            output_tokens=response.eval_count or 0,
            latency_ms=round((time.perf_counter() - start) * 1000),
        )


class ScriptedBackend:
    """Test double: returns prepared replies in order and records what it was sent."""

    def __init__(self, replies: list[Reply], model: str = "scripted-test-model"):
        self.model = model
        self._replies = list(replies)
        self.requests: list[dict] = []

    def chat(self, messages: list[dict], tools: list[dict] | None, schema: dict | None) -> Reply:
        self.requests.append({"messages": [dict(m) for m in messages], "tools": tools, "schema": schema})
        if not self._replies:
            raise LLMError("scripted backend ran out of replies")
        return self._replies.pop(0)


class LoggedLLM:
    """Wraps a backend and writes one dq.llm_calls row per call, successful or not."""

    def __init__(self, backend: Backend, conn: psycopg.Connection, settings: Settings):
        self.backend = backend
        self.conn = conn
        self.settings = settings
        self.investigation_id: int | None = None
        self.total_in = 0
        self.total_out = 0

    @property
    def model(self) -> str:
        return self.backend.model

    def chat(self, messages: list[dict], *, purpose: str, tools: list[dict] | None = None,
             schema: dict | None = None) -> Reply:
        start = time.perf_counter()
        try:
            reply = self.backend.chat(messages, tools, schema)
        except LLMError as exc:
            self._log(purpose, 0, 0, round((time.perf_counter() - start) * 1000), False, str(exc))
            raise
        self.total_in += reply.input_tokens
        self.total_out += reply.output_tokens
        self._log(purpose, reply.input_tokens, reply.output_tokens, reply.latency_ms, True, None)
        return reply

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        s = self.settings
        return (input_tokens * s.price_in_per_mtok + output_tokens * s.price_out_per_mtok) / 1_000_000

    def _log(self, purpose: str, tin: int, tout: int, latency_ms: int, success: bool, error: str | None) -> None:
        self.conn.execute(
            "INSERT INTO dq.llm_calls (purpose, model, input_tokens, output_tokens, cost_usd, latency_ms, "
            "success, error, investigation_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (purpose, self.model, tin, tout, self.cost(tin, tout), latency_ms, success, error, self.investigation_id),
        )
        self.conn.commit()


def make_backend(settings: Settings) -> Backend:
    return OllamaBackend(settings.ollama_url, settings.llm_model)
