package dev.dataguard.explainer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.client.ChatClient;

class ExplainerServiceTest {

    record Call(String purpose, String model, int in, int out, boolean success, String error) {
    }

    static class RecordingLog implements LlmCallLog {
        final List<Call> calls = new ArrayList<>();

        @Override
        public void record(String purpose, String model, int in, int out, long latencyMs, boolean success, String error) {
            calls.add(new Call(purpose, model, in, out, success, error));
        }
    }

    static final FailureRequest FAILURE = new FailureRequest(
            "orders", "orders_unique_id", "uniqueness", "critical",
            "25 duplicate keys", "0 duplicate keys", "25 values of (order_id) appear more than once",
            List.of(Map.of("order_id", 5779, "occurrences", 2)));

    static final String GOOD_ANSWER = """
            {"cause": "A batch of orders was loaded twice, probably by a retried load job.",
             "impact": "Revenue and order counts are overstated in finance reports.",
             "fixSteps": ["Delete the extra copies, keeping one row per order_id", "Make the load an upsert on order_id"],
             "confidence": "medium"}""";

    private ExplainerService service(FakeChatModel model, RecordingLog log) {
        return new ExplainerService(ChatClient.builder(model), log, "qwen2.5:3b");
    }

    @Test
    void explainsAFailureAndLogsTheCall() {
        FakeChatModel model = new FakeChatModel(GOOD_ANSWER);
        RecordingLog log = new RecordingLog();

        ExplainResponse response = service(model, log).explain(FAILURE);

        assertThat(response.explanation().cause()).contains("loaded twice");
        assertThat(response.explanation().fixSteps()).hasSize(2);
        assertThat(response.inputTokens()).isEqualTo(1200);
        assertThat(response.outputTokens()).isEqualTo(80);
        assertThat(response.model()).isEqualTo("qwen2.5:3b");
        assertThat(log.calls).containsExactly(new Call("explainer", "qwen2.5:3b", 1200, 80, true, null));
    }

    @Test
    void promptContainsTheFailureDetailsAndTheRules() {
        FakeChatModel model = new FakeChatModel(GOOD_ANSWER);
        service(model, new RecordingLog()).explain(FAILURE);

        String prompt = model.prompts.get(0).getContents();
        assertThat(prompt)
                .contains("orders_unique_id")
                .contains("Measured: 25 duplicate keys, allowed: 0 duplicate keys")
                .contains("order_id=5779")
                .contains("never claim it was done")                   // system prompt
                .contains("Your response should be in JSON format");   // added by Spring AI for the record
    }

    @Test
    void anIncompleteAnswerIsRejectedAndLoggedAsFailed() {
        FakeChatModel model = new FakeChatModel("""
                {"cause": "", "impact": "unknown", "fixSteps": [], "confidence": "sure"}""");
        RecordingLog log = new RecordingLog();

        assertThatThrownBy(() -> service(model, log).explain(FAILURE))
                .isInstanceOf(ExplainerException.class)
                .hasMessageContaining("incomplete");
        assertThat(log.calls).singleElement().satisfies(c -> {
            assertThat(c.success()).isFalse();
            assertThat(c.error()).isEqualTo("incomplete explanation");
        });
    }

    @Test
    void anAnswerThatIsNotJsonIsRejected() {
        RecordingLog log = new RecordingLog();
        assertThatThrownBy(() -> service(new FakeChatModel("Sorry, I cannot help."), log).explain(FAILURE))
                .isInstanceOf(ExplainerException.class);
        assertThat(log.calls).singleElement().extracting(Call::success).isEqualTo(false);
    }

    @Test
    void anUnreachableModelIsReportedClearly() {
        RecordingLog log = new RecordingLog();
        FakeChatModel down = new FakeChatModel(new IllegalStateException("I/O error: Connection refused"));

        assertThatThrownBy(() -> service(down, log).explain(FAILURE))
                .isInstanceOf(ExplainerException.class)
                .hasMessageContaining("did not answer")
                .hasMessageContaining("Connection refused");
        assertThat(log.calls).singleElement().extracting(Call::success).isEqualTo(false);
    }

    @Test
    void missingOptionalFieldsAreShownAsDashes() {
        FakeChatModel model = new FakeChatModel(GOOD_ANSWER);
        service(model, new RecordingLog()).explain(
                new FailureRequest("orders", "orders_schema", "schema", "high", null, null, null, null));
        assertThat(model.prompts.get(0).getContents()).contains("Measured: -, allowed: -").contains("Sample rows: []");
    }
}
