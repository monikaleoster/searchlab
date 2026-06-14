package com.searchlab.cli;

import com.searchlab.opensearch.IndexBootstrap;
import com.searchlab.opensearch.OpenSearchClientFactory;
import com.searchlab.rag.ContextBuilder;
import com.searchlab.rag.LlmApiException;
import com.searchlab.rag.LlmClient;
import com.searchlab.rag.LlmTimeoutException;
import com.searchlab.rag.RagResult;
import com.searchlab.search.Bm25Searcher;
import com.searchlab.search.SearchHit;
import org.opensearch.client.opensearch.OpenSearchClient;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;
import picocli.CommandLine.Parameters;

import java.util.List;
import java.util.concurrent.Callable;

@Command(name = "rag", description = "Retrieve passages via BM25 and generate an answer with an LLM")
public class RagCommand implements Callable<Integer> {

    static final String SYSTEM_PROMPT =
            "You are a search assistant. Answer the question using only the provided passages.\n" +
            "If the passages do not contain enough information, say so.";

    @Parameters(index = "0", description = "Natural language question", paramLabel = "<question>")
    private String question;

    @Option(names = "--top-k", defaultValue = "5",
            description = "Number of passages to retrieve (default: ${DEFAULT-VALUE})")
    private int topK;

    @Option(names = "--model",
            description = "LLM model to use (default: $SEARCHLAB_LLM_MODEL env var, or gpt-4o-mini)")
    private String model;

    @Override
    public Integer call() {
        RagResult result = execute(question, topK, resolveModel(model));
        if (result.error() != null) {
            System.err.println("Error: " + result.error());
            return 1;
        }
        System.out.println("Answer:");
        System.out.println(result.answer());
        System.out.println();
        if (!result.sources().isEmpty()) {
            System.out.println("Sources:");
            for (SearchHit hit : result.sources()) {
                System.out.printf("  [%d] %s  (score: %.3f)%n",
                        hit.rank(), hit.sourceFilename(), hit.score());
            }
        }
        return 0;
    }

    static String resolveModel(String override) {
        if (override != null && !override.isBlank()) return override;
        String envModel = System.getenv("SEARCHLAB_LLM_MODEL");
        return (envModel != null && !envModel.isBlank()) ? envModel : "gpt-4o-mini";
    }

    static RagResult execute(String question, int topK, String model) {
        if (question == null || question.isBlank()) {
            return new RagResult(null, List.of(), "Question cannot be empty.");
        }
        String apiKey = System.getenv("OPENAI_API_KEY");
        if (apiKey == null || apiKey.isBlank()) {
            return new RagResult(null, List.of(), "OPENAI_API_KEY environment variable is not set.");
        }
        try {
            OpenSearchClient client = OpenSearchClientFactory.createDefault();
            IndexBootstrap.ensureIndexExists(client);

            Bm25Searcher searcher = new Bm25Searcher(client);
            List<SearchHit> hits = searcher.search(question, topK);

            if (hits.isEmpty()) {
                return new RagResult("No passages retrieved for this query.", List.of(), null);
            }

            String context = new ContextBuilder().build(hits);
            String userPrompt = "Passages:\n" + context + "\n\nQuestion: " + question + "\n\nAnswer:";
            String answer = new LlmClient(model).complete(SYSTEM_PROMPT, userPrompt);
            return new RagResult(answer, hits, null);

        } catch (LlmTimeoutException e) {
            return new RagResult(null, List.of(), "LLM call timed out after 30 seconds.");
        } catch (LlmApiException e) {
            return new RagResult(null, List.of(),
                    "LLM API returned HTTP " + e.getStatusCode() + " — " + e.getMessage());
        } catch (Exception e) {
            return new RagResult(null, List.of(), e.getMessage());
        }
    }
}
