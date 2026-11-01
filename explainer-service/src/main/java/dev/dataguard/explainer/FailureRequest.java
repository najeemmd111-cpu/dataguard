package dev.dataguard.explainer;

import jakarta.validation.constraints.NotBlank;
import java.util.List;
import java.util.Map;

/** A failing data-quality result, in the shape the rules engine returns from GET /failures. */
public record FailureRequest(
        @NotBlank String dataset,
        @NotBlank String ruleId,
        @NotBlank String ruleType,
        @NotBlank String severity,
        String measuredValue,
        String threshold,
        String message,
        List<Map<String, Object>> sampleRows) {

    public List<Map<String, Object>> sampleRowsOrEmpty() {
        return sampleRows == null ? List.of() : sampleRows.stream().limit(5).toList();
    }
}
