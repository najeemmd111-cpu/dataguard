package dev.dataguard.explainer;

/** The model could not be reached or did not return a usable explanation. */
public class ExplainerException extends RuntimeException {

    public ExplainerException(String message, Throwable cause) {
        super(message, cause);
    }

    public ExplainerException(String message) {
        super(message);
    }
}
