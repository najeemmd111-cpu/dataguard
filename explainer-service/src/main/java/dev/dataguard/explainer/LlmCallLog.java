package dev.dataguard.explainer;

/** Records every model call: the same dq.llm_calls table the Python agent writes to. */
public interface LlmCallLog {

    void record(String purpose, String model, int inputTokens, int outputTokens, long latencyMs,
                boolean success, String error);
}
