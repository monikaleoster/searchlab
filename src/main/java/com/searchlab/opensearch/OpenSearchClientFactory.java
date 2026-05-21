package com.searchlab.opensearch;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.apache.http.HttpHost;
import org.opensearch.client.RestClient;
import org.opensearch.client.json.jackson.JacksonJsonpMapper;
import org.opensearch.client.opensearch.OpenSearchClient;
import org.opensearch.client.transport.rest_client.RestClientTransport;

public class OpenSearchClientFactory {

    public static OpenSearchClient create(String host, int port) {
        ObjectMapper mapper = new ObjectMapper()
                .registerModule(new JavaTimeModule())
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

        RestClient restClient = RestClient.builder(new HttpHost(host, port, "http")).build();
        RestClientTransport transport = new RestClientTransport(restClient, new JacksonJsonpMapper(mapper));
        return new OpenSearchClient(transport);
    }

    public static OpenSearchClient createDefault() {
        return create("localhost", 9200);
    }
}
