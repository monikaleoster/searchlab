package com.searchlab.rag;

public class LlmApiException extends RuntimeException {

    private final int statusCode;

    public LlmApiException(int statusCode, String body) {
        super("LLM API error " + statusCode + ": " + body);
        this.statusCode = statusCode;
    }

    public int getStatusCode() {
        return statusCode;
    }
}
