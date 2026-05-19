package com.searchlab.search;

import com.searchlab.opensearch.IndexBootstrap;
import org.opensearch.client.opensearch.OpenSearchClient;
import org.opensearch.client.opensearch._types.query_dsl.Query;
import org.opensearch.client.opensearch.core.SearchRequest;
import org.opensearch.client.opensearch.core.SearchResponse;
import org.opensearch.client.opensearch.core.search.Hit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class Bm25Searcher {

    private static final Logger log = LoggerFactory.getLogger(Bm25Searcher.class);
    private static final int SNIPPET_LENGTH = 200;

    private final OpenSearchClient client;

    public Bm25Searcher(OpenSearchClient client) {
        this.client = client;
    }

    @SuppressWarnings("unchecked")
    public List<SearchHit> search(String queryString, int topK) throws IOException {
        Query matchQuery = Query.of(q -> q
                .match(m -> m.field("chunk_text").query(v -> v.stringValue(queryString)))
        );

        SearchRequest request = SearchRequest.of(r -> r
                .index(IndexBootstrap.INDEX_NAME)
                .query(matchQuery)
                .size(topK)
        );

        SearchResponse<Map> response = client.search(request, Map.class);

        List<SearchHit> results = new ArrayList<>();
        int rank = 1;

        for (Hit<Map> hit : response.hits().hits()) {
            Map<String, Object> source = hit.source();
            if (source == null) continue;

            String chunkText = (String) source.getOrDefault("chunk_text", "");
            String sourceFilename = (String) source.getOrDefault("source_filename", "");
            Object pageObj = source.get("page_number");
            int pageNumber = pageObj instanceof Number n ? n.intValue() : 0;

            String snippet = chunkText.length() > SNIPPET_LENGTH
                    ? chunkText.substring(0, SNIPPET_LENGTH)
                    : chunkText;

            double score = hit.score() != null ? hit.score() : 0.0;
            results.add(new SearchHit(rank++, score, sourceFilename, pageNumber, snippet));
        }

        log.debug("Query '{}' returned {} hits", queryString, results.size());
        return results;
    }
}
