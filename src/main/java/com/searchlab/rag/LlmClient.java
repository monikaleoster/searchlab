package com.searchlab.rag;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Duration;

public class LlmClient {

    private static final String OPENAI_URL = "https://api.openai.com/v1/chat/completions";
    private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(30);
    private static final ObjectMapper JSON = new ObjectMapper();

    private final String model;
    private final String apiKey;
    private final String url;
    private final HttpClient http;
    private final Duration timeout;

    public LlmClient(String model) {
        String key = System.getenv("OPENAI_API_KEY");
        if (key == null || key.isBlank()) {
            throw new IllegalStateException("OPENAI_API_KEY environment variable is not set");
        }
        this.model = model;
        this.apiKey = key;
        this.url = OPENAI_URL;
        this.timeout = DEFAULT_TIMEOUT;
        this.http = HttpClient.newBuilder().connectTimeout(timeout).build();
    }

    LlmClient(String model, String apiKey, String url, HttpClient http, Duration timeout) {
        if (apiKey == null || apiKey.isBlank()) {
            throw new IllegalStateException("OPENAI_API_KEY environment variable is not set");
        }
        this.model = model;
        this.apiKey = apiKey;
        this.url = url;
        this.http = http;
        this.timeout = timeout;
    }

    public String complete(String systemPrompt, String userPrompt) {
        try {
            ObjectNode body = JSON.createObjectNode();
            body.put("model", model);
            body.put("temperature", 0);
            ArrayNode messages = body.putArray("messages");
            messages.addObject().put("role", "system").put("content", systemPrompt);
            messages.addObject().put("role", "user").put("content", userPrompt);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + apiKey)
                    .timeout(timeout)
                    .POST(HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(body)))
                    .build();

            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new LlmApiException(response.statusCode(), response.body());
            }

            return JSON.readTree(response.body())
                    .path("choices").path(0).path("message").path("content").asText();

        } catch (LlmApiException e) {
            throw e;
        } catch (HttpTimeoutException e) {
            throw new LlmTimeoutException(e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("LLM call interrupted", e);
        } catch (IOException e) {
            throw new RuntimeException("LLM call failed: " + e.getMessage(), e);
        }
    }
}
