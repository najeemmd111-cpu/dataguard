# Explainer service (Phase 4b): Java, Spring Boot, Spring AI

A small Spring Boot service that turns one failing data-quality result into a short, structured explanation: **cause**, **impact**, **fix steps** and **confidence**. It uses [Spring AI](https://docs.spring.io/spring-ai/reference/) with the same free local model as the Python agent (`qwen2.5:3b` through Ollama).

| | |
|---|---|
| Stack | Java 21, Spring Boot 3.5.14, Spring AI 1.1.7 (`spring-ai-starter-model-ollama`) |
| Endpoint | `POST /explain`, port 8081 |
| Input | one item from the rules engine's `GET /failures`, as-is (snake_case JSON) |
| Output | `{explanation: {cause, impact, fix_steps, confidence}, model, input_tokens, output_tokens, latency_ms}` |

How it differs from the Python agent: the agent investigates, calling tools for several rounds. The explainer makes **one** model call with the failure details and returns an explanation, so it is quick and suits places like an alert email or a button.

## Run it

You don't need Java installed: Docker builds the service with Maven. Ollama must be running on your Mac.

```bash
docker compose --profile explainer up -d --build     # first build downloads Maven and Spring (a few minutes)
```

Explain the first current failure:

```bash
curl -s localhost:8000/failures \
  | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)[0]))' \
  | curl -s -X POST localhost:8081/explain -H 'content-type: application/json' -d @- \
  | python3 -m json.tool
```

Health check: `curl localhost:8081/actuator/health`.

## How it works

- `ExplainerService` builds a `ChatClient` with a **system prompt**: use only the given details, never claim anything was done. It fills a **prompt template** with the failure (rule, measured vs allowed, message, up to 5 sample rows).
- `.call().responseEntity(Explanation.class)` asks Spring AI for **structured output**. Spring AI derives a JSON schema from the `Explanation` record, adds format instructions to the prompt, and parses the answer back into the record. It also returns the raw `ChatResponse`, with **token usage**.
- The answer is **validated**: a blank cause, no fix steps or an unknown confidence level gives a `502` with a clear message instead of a half-empty explanation.
- Every call, successful or not, is written to **`dq.llm_calls`** with purpose `explainer`, so it appears on the dashboard's **AI usage** page next to the agent's calls. Logging is best effort: the explanation is still returned if the database is down.
- Errors: an unreachable model or an unusable answer → `502` (`ProblemDetail`); a request missing `dataset`, `rule_id`, `rule_type` or `severity` → `400`.

## Result

First run on a MacBook Air with `qwen2.5:3b`, explaining `orders/orders_fresh` (the seeded stopped-ETL failure): the cause was right ("the data ingestion process … interrupted or delayed"), the first three fix steps were relevant, and the fourth was generic. Full answer: [examples/orders_fresh.json](examples/orders_fresh.json).

| | Explainer (Spring AI, one call) | Root-cause agent (Python, tools) |
|---|---|---|
| Model calls | 1 | about 4–5 |
| Tokens | 638 | about 8,800 |
| Time | 6.8 s | about 30 s |
| Checks the data, cites docs | no | yes (read-only SQL, re-ranked search) |
| Good for | quick summaries in alerts or buttons | real investigations |

The explainer is about 14× cheaper and 4× faster. The agent is slower but grounded in evidence.

## Tests

```bash
mvn verify          # needs Java 21 and Maven; CI runs this on every push
```

- `ExplainerServiceTest`: a fake `ChatModel` returns prepared answers. It checks the parsed explanation and token counts, that the prompt contains the failure details, the system prompt and Spring AI's JSON format instructions, and the rejection of incomplete or non-JSON answers and of an unreachable model, each logged as a failed call.
- `ExplainControllerTest` (`@WebMvcTest`): snake_case input and output, `400` on missing fields, `502` on model problems.
- `ExplainerApplicationTests` (`@SpringBootTest`): the whole application starts with the real Spring AI Ollama wiring.

No test needs Ollama or a database.

## Settings

| Variable | Default |
|---|---|
| `OLLAMA_URL` | `http://localhost:11434` (`host.docker.internal` in Docker) |
| `DG_LLM_MODEL` | `qwen2.5:3b` |
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://localhost:5432/dataguard` |
