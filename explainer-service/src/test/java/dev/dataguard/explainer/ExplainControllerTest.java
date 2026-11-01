package dev.dataguard.explainer;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(ExplainController.class)
class ExplainControllerTest {

    @Autowired
    MockMvc mvc;

    @MockitoBean
    ExplainerService service;

    // The same shape as an item from the rules engine's GET /failures (snake_case, extra fields ignored).
    static final String FAILURE_JSON = """
            {"result_id": 13, "dataset": "orders", "rule_id": "orders_fresh", "rule_type": "freshness",
             "severity": "critical", "passed": false, "measured_value": "72.4h", "threshold": "24h",
             "message": "latest updated_at is 72.4h old", "sample_rows": [{"age_hours": 72.4}], "annotations": []}""";

    @Test
    void returnsTheExplanationInSnakeCase() throws Exception {
        given(service.explain(any())).willReturn(new ExplainResponse(
                new Explanation("The sales ETL stopped.", "Finance sees stale orders.",
                        List.of("Restart the sales ETL job"), "medium"),
                "qwen2.5:3b", 1200, 80, 9000));

        mvc.perform(post("/explain").contentType(MediaType.APPLICATION_JSON).content(FAILURE_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.explanation.cause").value("The sales ETL stopped."))
                .andExpect(jsonPath("$.explanation.fix_steps[0]").value("Restart the sales ETL job"))
                .andExpect(jsonPath("$.input_tokens").value(1200))
                .andExpect(jsonPath("$.latency_ms").value(9000));
    }

    @Test
    void rejectsAFailureWithoutRequiredFields() throws Exception {
        mvc.perform(post("/explain").contentType(MediaType.APPLICATION_JSON).content("{\"dataset\": \"orders\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void reportsModelProblemsAsBadGateway() throws Exception {
        given(service.explain(any())).willThrow(new ExplainerException("The language model did not answer: refused"));

        mvc.perform(post("/explain").contentType(MediaType.APPLICATION_JSON).content(FAILURE_JSON))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.title").value("Explanation not available"))
                .andExpect(jsonPath("$.detail").value("The language model did not answer: refused"));
    }
}
