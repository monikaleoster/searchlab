package com.searchlab.rag;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.InetSocketAddress;
import java.net.http.HttpClient;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.*;

class LlmClientTest {

    private HttpServer server;
    private String baseUrl;

    @BeforeEach
    void startServer() throws Exception {
        server = HttpServer.create(new InetSocketAddress(0), 0);
        server.start();
        baseUrl = "http://localhost:" + server.getAddress().getPort() + "/v1/chat/completions";
    }

    @AfterEach
    void stopServer() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    void missingApiKeyThrowsIllegalState() {
        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> new LlmClient("gpt-4o-mini", "", baseUrl,
                        HttpClient.newHttpClient(), Duration.ofSeconds(5)));
        assertTrue(ex.getMessage().contains("OPENAI_API_KEY"));
    }

    @Test
    void status429ThrowsLlmApiException() throws Exception {
        server.createContext("/v1/chat/completions", exchange -> {
            byte[] body = "rate limited".getBytes();
            exchange.sendResponseHeaders(429, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });

        LlmClient client = new LlmClient("gpt-4o-mini", "test-key", baseUrl,
                HttpClient.newHttpClient(), Duration.ofSeconds(5));

        LlmApiException ex = assertThrows(LlmApiException.class,
                () -> client.complete("sys", "user"));
        assertEquals(429, ex.getStatusCode());
    }

    @Test
    void timeoutThrowsLlmTimeoutException() throws Exception {
        server.createContext("/v1/chat/completions", exchange -> {
            try {
                Thread.sleep(2000);
            } catch (InterruptedException ignored) {
            }
            exchange.sendResponseHeaders(200, 0);
            exchange.close();
        });

        LlmClient client = new LlmClient("gpt-4o-mini", "test-key", baseUrl,
                HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build(),
                Duration.ofMillis(100));

        assertThrows(LlmTimeoutException.class,
                () -> client.complete("sys", "user"));
    }
}
