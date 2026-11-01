package dev.dataguard.explainer;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ExplainController {

    private final ExplainerService service;

    public ExplainController(ExplainerService service) {
        this.service = service;
    }

    /** Explain one failing result. Accepts an item from the rules engine's GET /failures as-is. */
    @PostMapping("/explain")
    public ExplainResponse explain(@Valid @RequestBody FailureRequest failure) {
        return service.explain(failure);
    }

    @ExceptionHandler(ExplainerException.class)
    ProblemDetail modelProblem(ExplainerException e) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_GATEWAY, e.getMessage());
        problem.setTitle("Explanation not available");
        return problem;
    }
}
