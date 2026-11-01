package dev.dataguard.explainer;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/** The whole application starts with the real Spring AI Ollama wiring (no model call is made). */
@SpringBootTest
class ExplainerApplicationTests {

    @Autowired
    ExplainerService service;

    @Autowired
    LlmCallLog callLog;

    @Test
    void contextLoads() {
        assertThat(service).isNotNull();
        assertThat(callLog).isInstanceOf(JdbcLlmCallLog.class);
    }
}
