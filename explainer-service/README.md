# Explainer service (Phase 4) — Java, Spring Boot, Spring AI

Generate the project at https://start.spring.io:

- Project: Maven · Language: Java · Spring Boot 3.x · Java 21
- Group `dev.dataguard`, Artifact `explainer`
- Dependencies: **Spring Web**, **Validation**, **Actuator**, and one Spring AI model starter (Anthropic, OpenAI or Ollama)

Unzip it into this folder.

## What to build

`POST /explain` receives a failing result (as returned by `GET /failures`) and returns:

```java
public record Explanation(String cause, String impact, String fix, String confidence) {}
```

Core of the controller:

```java
@PostMapping("/explain")
Explanation explain(@RequestBody @Valid FailureDto failure) {
    return chatClient.prompt()
        .system("You explain data-quality failures to data engineers. Be concrete and short.")
        .user(u -> u.text("""
            Dataset: {dataset}
            Rule: {rule} ({type}, severity {severity})
            Measured: {measured} vs threshold {threshold}
            Message: {message}
            Sample rows: {samples}
            """)
            .param("dataset", failure.dataset())
            /* ... other params ... */)
        .call()
        .entity(Explanation.class);   // Spring AI structured output
}
```

## Tests

- Unit test with a mocked `ChatClient` (assert the prompt contains the rule id; assert the record mapping).
- One `@SpringBootTest` integration test, skipped when no API key is set.

## Hook it up

- Log every call into `dq.llm_calls` (purpose = `explainer`) with Spring JDBC.
- Register it as a tool of the phase-3 root-cause agent.
- Run on port 8081.
