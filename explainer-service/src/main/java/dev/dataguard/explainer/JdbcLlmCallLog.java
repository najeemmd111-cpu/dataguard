package dev.dataguard.explainer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
class JdbcLlmCallLog implements LlmCallLog {

    private static final Logger log = LoggerFactory.getLogger(JdbcLlmCallLog.class);

    private final JdbcTemplate jdbc;

    JdbcLlmCallLog(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public void record(String purpose, String model, int inputTokens, int outputTokens, long latencyMs,
                       boolean success, String error) {
        try {
            jdbc.update("INSERT INTO dq.llm_calls (purpose, model, input_tokens, output_tokens, cost_usd, latency_ms, "
                            + "success, error) VALUES (?, ?, ?, ?, 0, ?, ?, ?)",
                    purpose, model, inputTokens, outputTokens, (int) latencyMs, success, error);
        } catch (DataAccessException e) {
            // Logging is best effort: an explanation is still returned if the database is unavailable.
            log.warn("Could not record the model call in dq.llm_calls: {}", e.getMostSpecificCause().getMessage());
        }
    }
}
