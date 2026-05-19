package com.searchlab.cli;

import com.searchlab.opensearch.IndexBootstrap;
import com.searchlab.opensearch.OpenSearchClientFactory;
import com.searchlab.search.Bm25Searcher;
import com.searchlab.search.SearchHit;
import org.opensearch.client.opensearch.OpenSearchClient;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;
import picocli.CommandLine.Parameters;

import java.util.List;

@Command(name = "query", description = "BM25 search against the indexed chunks")
public class QueryCommand implements Runnable {

    @Parameters(index = "0", description = "Query string", paramLabel = "<query>")
    private String queryString;

    @Option(names = "--top-k", defaultValue = "5", description = "Number of results (default: ${DEFAULT-VALUE})")
    private int topK;

    @Override
    public void run() {
        try {
            OpenSearchClient client = OpenSearchClientFactory.createDefault();
            IndexBootstrap.ensureIndexExists(client);

            Bm25Searcher searcher = new Bm25Searcher(client);
            List<SearchHit> hits = searcher.search(queryString, topK);

            if (hits.isEmpty()) {
                System.out.println("No results found for: " + queryString);
                return;
            }

            System.out.printf("%-4s  %-7s  %-30s  %-4s  %s%n",
                    "Rank", "Score", "Source", "Page", "Snippet");
            System.out.println("-".repeat(100));

            for (SearchHit hit : hits) {
                String snippet = hit.snippet().replace('\n', ' ').replace('\r', ' ');
                System.out.printf("%-4d  %-7.4f  %-30s  %-4d  %s%n",
                        hit.rank(),
                        hit.score(),
                        truncate(hit.sourceFilename(), 30),
                        hit.pageNumber(),
                        snippet);
            }

        } catch (Exception e) {
            System.err.println("Query failed: " + e.getMessage());
            throw new picocli.CommandLine.ExecutionException(
                    new picocli.CommandLine(this), "Query failed", e);
        }
    }

    private static String truncate(String s, int max) {
        return s.length() <= max ? s : s.substring(0, max - 1) + "…";
    }
}
