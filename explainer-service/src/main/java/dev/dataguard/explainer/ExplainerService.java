package dev.dataguard.explainer;

import java.util.Map;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.ResponseEntity;
import org.springframework.ai.chat.metadata.Usage;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class ExplainerService {

    static final String PURPOSE = "explainer";

    static final String SYSTEM_PROMPT = """
            You explain data-quality failures to data engineers.
            Use only the failure details you are given. Do not invent numbers, events or systems.
            You cannot change anything: describe what a person should do, never claim it was done.
            Keep each field short and concrete.""";

    static final String USER_PROMPT = """
            A data-quality rule failed.
            Dataset: {dataset}
            Rule: {ruleId} (type: {ruleType}, severity: {severity})
            Measured: {measured}, allowed: {threshold}
            Message: {message}
            Sample rows: {samples}

            Explain:
            - cause: the most likely cause, in one or two sentences
            - impact: who or what is affected if nobody acts
            - fixSteps: 2 to 4 concrete steps for a person to take
            - confidence: low, medium or high""";

    private final ChatClient chatClient;
    private final LlmCallLog callLog;
    private final String model;

    public ExplainerService(ChatClient.Builder builder, LlmCallLog callLog,
                            @Value("${spring.ai.ollama.chat.options.model:unknown}") String model) {
        this.chatClient = builder.defaultSystem(SYSTEM_PROMPT).build();
        this.callLog = callLog;
        this.model = model;
    }

    public ExplainResponse explain(FailureRequest failure) {
        long start = System.nanoTime();
        ResponseEntity<ChatResponse, Explanation> result;
        try {
            result = chatClient.prompt()
                    .user(u -> u.text(USER_PROMPT).params(Map.of(
                            "dataset", failure.dataset(),
                            "ruleId", failure.ruleId(),
                            "ruleType", failure.ruleType(),
                            "severity", failure.severity(),
                            "measured", orDash(failure.measuredValue()),
                            "threshold", orDash(failure.threshold()),
                            "message", orDash(failure.message()),
                            "samples", failure.sampleRowsOrEmpty().toString())))
                    .call()
                    .responseEntity(Explanation.class);
        } catch (RuntimeException e) {
            long ms = elapsedMs(start);
            callLog.record(PURPOSE, model, 0, 0, ms, false, e.getMessage());
            throw new ExplainerException("The language model did not answer: " + e.getMessage(), e);
        }

        long ms = elapsedMs(start);
        int in = 0;
        int out = 0;
        ChatResponse response = result.getResponse();
        if (response != null && response.getMetadata() != null) {
            Usage usage = response.getMetadata().getUsage();
            if (usage != null) {
                in = usage.getPromptTokens() == null ? 0 : usage.getPromptTokens();
                out = usage.getCompletionTokens() == null ? 0 : usage.getCompletionTokens();
            }
        }

        Explanation explanation = result.getEntity();
        if (explanation == null || !explanation.isComplete()) {
            callLog.record(PURPOSE, model, in, out, ms, false, "incomplete explanation");
            throw new ExplainerException("The language model returned an incomplete explanation.");
        }
        callLog.record(PURPOSE, model, in, out, ms, true, null);
        return new ExplainResponse(explanation, model, in, out, ms);
    }

    private static String orDash(String value) {
        return value == null || value.isBlank() ? "-" : value;
    }

    private static long elapsedMs(long startNanos) {
        return (System.nanoTime() - startNanos) / 1_000_000;
    }
}
