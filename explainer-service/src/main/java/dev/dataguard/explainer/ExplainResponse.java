package dev.dataguard.explainer;

public record ExplainResponse(Explanation explanation, String model, int inputTokens, int outputTokens, long latencyMs) {
}
