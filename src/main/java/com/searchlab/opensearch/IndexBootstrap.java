package com.searchlab.opensearch;

import org.opensearch.client.opensearch.OpenSearchClient;
import org.opensearch.client.opensearch._types.mapping.*;
import org.opensearch.client.opensearch.indices.CreateIndexRequest;
import org.opensearch.client.opensearch.indices.ExistsRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.Map;

public class IndexBootstrap {

    private static final Logger log = LoggerFactory.getLogger(IndexBootstrap.class);
    public static final String INDEX_NAME = "searchlab-v0";

    public static void ensureIndexExists(OpenSearchClient client) throws IOException {
        boolean exists = client.indices()
                .exists(ExistsRequest.of(r -> r.index(INDEX_NAME)))
                .value();

        if (exists) {
            log.debug("Index '{}' already exists", INDEX_NAME);
            return;
        }

        log.info("Creating index '{}'", INDEX_NAME);
        client.indices().create(CreateIndexRequest.of(req -> req
                .index(INDEX_NAME)
                .mappings(m -> m.properties(buildProperties()))
        ));
        log.info("Index '{}' created", INDEX_NAME);
    }

    private static Map<String, Property> buildProperties() {
        return Map.of(
                "chunk_text",      Property.of(p -> p.text(t -> t.analyzer("standard"))),
                "source_filename", Property.of(p -> p.keyword(k -> k)),
                "chunk_id",        Property.of(p -> p.keyword(k -> k)),
                "page_number",     Property.of(p -> p.integer(i -> i)),
                "chunk_position",  Property.of(p -> p.integer(i -> i)),
                "ingested_at",     Property.of(p -> p.date(d -> d))
        );
    }
}
