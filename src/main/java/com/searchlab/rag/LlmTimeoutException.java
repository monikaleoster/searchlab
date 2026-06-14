package com.searchlab.rag;

public class LlmTimeoutException extends RuntimeException {

    public LlmTimeoutException(Throwable cause) {
        super("LLM call exceeded 30s timeout", cause);
    }
}
