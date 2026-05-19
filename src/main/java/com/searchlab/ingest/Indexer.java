package com.searchlab.ingest;

import com.searchlab.opensearch.IndexBootstrap;
import org.opensearch.client.opensearch.OpenSearchClient;
import org.opensearch.client.opensearch.core.BulkRequest;
import org.opensearch.client.opensearch.core.BulkResponse;
import org.opensearch.client.opensearch.core.bulk.BulkOperation;
import org.opensearch.client.opensearch.core.bulk.IndexOperation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class Indexer {

    private static final Logger log = LoggerFactory.getLogger(Indexer.class);

    private final OpenSearchClient client;

    public Indexer(OpenSearchClient client) {
        this.client = client;
    }

    public int index(List<Chunk> chunks, String sourceFilename) throws IOException {
        if (chunks.isEmpty()) {
            return 0;
        }

        List<BulkOperation> operations = new ArrayList<>(chunks.size());
        String ingestedAt = Instant.now().toString();

        for (Chunk chunk : chunks) {
            String chunkId = ChunkId.compute(sourceFilename, chunk.position());

            Map<String, Object> doc = Map.of(
                    "chunk_id",        chunkId,
                    "chunk_text",      chunk.text(),
                    "source_filename", sourceFilename,
                    "page_number",     chunk.pageNumber(),
                    "chunk_position",  chunk.position(),
                    "ingested_at",     ingestedAt
            );

            operations.add(BulkOperation.of(op -> op
                    .index(IndexOperation.of(i -> i
                            .index(IndexBootstrap.INDEX_NAME)
                            .id(chunkId)
                            .document(doc)
                    ))
            ));
        }

        BulkResponse response = client.bulk(BulkRequest.of(r -> r.operations(operations)));

        if (response.errors()) {
            response.items().stream()
                    .filter(item -> item.error() != null)
                    .forEach(item -> log.error("Bulk index error on id={}: {}", item.id(), item.error().reason()));
            throw new IOException("Bulk indexing completed with errors — see logs above");
        }

        log.debug("Indexed {} chunks for '{}'", chunks.size(), sourceFilename);
        return chunks.size();
    }
}
