package dev.dataguard.explainer;

import java.util.List;

/** What the model must return. Spring AI turns this record into a JSON schema and parses the answer back. */
public record Explanation(String cause, String impact, List<String> fixSteps, String confidence) {

    boolean isComplete() {
        return cause != null && !cause.isBlank()
                && impact != null && !impact.isBlank()
                && fixSteps != null && !fixSteps.isEmpty()
                && confidence != null && List.of("low", "medium", "high").contains(confidence.toLowerCase());
    }
}
