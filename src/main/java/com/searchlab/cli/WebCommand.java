package com.searchlab.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.searchlab.ingest.Chunk;
import com.searchlab.ingest.Chunker;
import com.searchlab.ingest.Indexer;
import com.searchlab.ingest.PageText;
import com.searchlab.ingest.PdfParser;
import com.searchlab.opensearch.IndexBootstrap;
import com.searchlab.opensearch.OpenSearchClientFactory;
import com.searchlab.rag.ContextBuilder;
import com.searchlab.rag.LlmApiException;
import com.searchlab.rag.LlmClient;
import com.searchlab.rag.LlmTimeoutException;
import com.searchlab.rag.RagResult;
import com.searchlab.search.SearchHit;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.opensearch.client.opensearch.OpenSearchClient;
import org.opensearch.client.opensearch._types.query_dsl.Query;
import org.opensearch.client.opensearch.core.SearchRequest;
import org.opensearch.client.opensearch.core.SearchResponse;
import org.opensearch.client.opensearch.core.search.Hit;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;

@Command(name = "serve", description = "Launch a local web UI for RAG queries and eval reports")
public class WebCommand implements Callable<Integer> {

    @Option(names = "--port", defaultValue = "8080",
            description = "Port to listen on (default: ${DEFAULT-VALUE})")
    private int port;

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final Map<String, String> DATASET_INDEX = Map.of(
            "nfcorpus", "searchlab-nfcorpus",
            "fiqa",     "searchlab-fiqa"
    );

    private static final String EVAL_DIR     = "searchlab-eval";
    private static final String RESULTS_DIR  = "searchlab-eval/results";

    // ── Server startup ────────────────────────────────────────────────────────

    @Override
    public Integer call() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/",                  this::handleRoot);
        server.createContext("/rag",               this::handleRag);
        server.createContext("/api/query",         this::handleApiQuery);
        server.createContext("/api/ingest",        this::handleApiIngest);
        server.createContext("/api/eval/stream",   this::handleEvalStream);
        server.createContext("/api/eval/runs",     this::handleEvalRuns);
        server.createContext("/api/eval/results",  this::handleEvalResults);
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();
        System.out.printf("SearchLab UI → http://localhost:%d%n", port);
        System.out.println("Press Ctrl+C to stop.");
        Thread.currentThread().join();
        return 0;
    }

    // ── Route handlers ────────────────────────────────────────────────────────

    private void handleRoot(HttpExchange ex) throws IOException {
        if (!"GET".equals(ex.getRequestMethod())) { ex.sendResponseHeaders(405, -1); return; }
        boolean hasKey = !isBlank(System.getenv("OPENAI_API_KEY"));
        byte[] body = HTML
                .replace("__OPENAI_KEY_SET__", String.valueOf(hasKey))
                .getBytes(StandardCharsets.UTF_8);
        sendBytes(ex, "text/html; charset=utf-8", body);
    }

    @SuppressWarnings("unchecked")
    private void handleRag(HttpExchange ex) throws IOException {
        if (!"POST".equals(ex.getRequestMethod())) { ex.sendResponseHeaders(405, -1); return; }
        Map<String, String> params = parseForm(
                new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
        String question = params.getOrDefault("question", "").strip();
        int    topK     = parseInt(params.getOrDefault("topK", "5"), 5);
        String model    = params.getOrDefault("model", "").strip();
        String dataset  = params.getOrDefault("dataset", "default");
        String indexName = "default".equals(dataset)
                ? IndexBootstrap.DEFAULT_INDEX_NAME
                : DATASET_INDEX.getOrDefault(dataset, IndexBootstrap.DEFAULT_INDEX_NAME);

        ObjectNode resp = JSON.createObjectNode();
        try {
            if (isBlank(question)) { resp.put("error", "Question cannot be empty."); sendBytes(ex, "application/json", JSON.writeValueAsBytes(resp)); return; }
            if (isBlank(System.getenv("OPENAI_API_KEY"))) { resp.put("error", "OPENAI_API_KEY environment variable is not set."); sendBytes(ex, "application/json", JSON.writeValueAsBytes(resp)); return; }

            // BM25 search against the selected index
            OpenSearchClient client = OpenSearchClientFactory.createDefault();
            Query matchQuery = Query.of(q -> q
                    .match(m -> m.field("chunk_text").query(v -> v.stringValue(question))));
            SearchRequest req = SearchRequest.of(r -> r.index(indexName).query(matchQuery).size(topK));
            SearchResponse<Map> response = client.search(req, Map.class);

            List<SearchHit> hits = new ArrayList<>();
            int rank = 1;
            for (Hit<Map> hit : response.hits().hits()) {
                Map<String, Object> src = hit.source();
                if (src == null) continue;
                String text    = (String) src.getOrDefault("chunk_text", "");
                String snippet = text.length() > 200 ? text.substring(0, 200) : text;
                int    page    = src.get("page_number") instanceof Number n ? n.intValue() : 0;
                hits.add(new SearchHit(rank++, hit.score() != null ? hit.score() : 0.0,
                        (String) src.getOrDefault("source_filename", ""), page, snippet));
            }

            if (hits.isEmpty()) {
                resp.put("answer", "No passages retrieved for this query.");
                resp.putArray("sources");
            } else {
                String context    = new ContextBuilder().build(hits);
                String userPrompt = "Passages:\n" + context + "\n\nQuestion: " + question + "\n\nAnswer:";
                String answer     = new LlmClient(RagCommand.resolveModel(isBlank(model) ? null : model))
                                        .complete(RagCommand.SYSTEM_PROMPT, userPrompt);
                resp.put("answer", answer);
                resp.put("index",  indexName);
                ArrayNode sources = resp.putArray("sources");
                for (SearchHit hit : hits) {
                    sources.addObject()
                           .put("rank",     hit.rank())
                           .put("filename", hit.sourceFilename())
                           .put("page",     hit.pageNumber())
                           .put("score",    hit.score());
                }
            }
        } catch (LlmTimeoutException e) {
            resp.put("error", "LLM call timed out after 30 seconds.");
        } catch (LlmApiException e) {
            resp.put("error", "LLM API returned HTTP " + e.getStatusCode() + " — " + e.getMessage());
        } catch (Exception e) {
            resp.put("error", e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName());
        }
        sendBytes(ex, "application/json", JSON.writeValueAsBytes(resp));
    }

    @SuppressWarnings("unchecked")
    private void handleApiQuery(HttpExchange ex) throws IOException {
        if (!"POST".equals(ex.getRequestMethod())) { ex.sendResponseHeaders(405, -1); return; }
        Map<String, String> params = parseForm(
                new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
        String queryText = params.getOrDefault("query", "").strip();
        int    topK      = parseInt(params.getOrDefault("topK", "5"), 5);
        String dataset   = params.getOrDefault("dataset", "nfcorpus");
        String indexName = DATASET_INDEX.getOrDefault(dataset, IndexBootstrap.DEFAULT_INDEX_NAME);

        ObjectNode resp = JSON.createObjectNode();
        try {
            if (isBlank(queryText)) { resp.put("error", "Query cannot be empty."); }
            else {
                OpenSearchClient client = OpenSearchClientFactory.createDefault();
                Query matchQuery = Query.of(q -> q
                        .match(m -> m.field("chunk_text").query(v -> v.stringValue(queryText))));
                SearchRequest req = SearchRequest.of(r -> r
                        .index(indexName).query(matchQuery).size(topK));
                SearchResponse<Map> response = client.search(req, Map.class);

                ArrayNode hits = resp.putArray("hits");
                int rank = 1;
                for (Hit<Map> hit : response.hits().hits()) {
                    Map<String, Object> src = hit.source();
                    if (src == null) continue;
                    String text = (String) src.getOrDefault("chunk_text", "");
                    String snippet = text.length() > 200 ? text.substring(0, 200) : text;
                    int page = src.get("page_number") instanceof Number n ? n.intValue() : 0;
                    hits.addObject()
                        .put("rank",     rank++)
                        .put("score",    hit.score() != null ? hit.score() : 0.0)
                        .put("filename", (String) src.getOrDefault("source_filename", ""))
                        .put("page",     page)
                        .put("snippet",  snippet);
                }
                resp.put("index", indexName);
            }
        } catch (Exception e) {
            resp.put("error", e.getMessage());
        }
        sendBytes(ex, "application/json", JSON.writeValueAsBytes(resp));
    }

    private void handleApiIngest(HttpExchange ex) throws IOException {
        if (!"POST".equals(ex.getRequestMethod())) { ex.sendResponseHeaders(405, -1); return; }
        Map<String, String> params = parseForm(
                new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
        String pdfPath = params.getOrDefault("pdfPath", "").strip();

        ObjectNode resp = JSON.createObjectNode();
        try {
            if (isBlank(pdfPath)) {
                resp.put("error", "PDF path is required.");
            } else if (!pdfPath.toLowerCase().endsWith(".pdf")) {
                resp.put("error", "File must be a .pdf");
            } else {
                Path path = Path.of(pdfPath);
                if (!Files.exists(path)) {
                    resp.put("error", "File not found: " + pdfPath);
                } else {
                    OpenSearchClient client = OpenSearchClientFactory.createDefault();
                    IndexBootstrap.ensureIndexExists(client);

                    List<PageText> pages  = new PdfParser().parse(path);
                    List<Chunk>   chunks  = new Chunker().chunk(pages);
                    int           count   = new Indexer(client).index(chunks, path.getFileName().toString());

                    resp.put("chunksIndexed", count);
                    resp.put("filename", path.getFileName().toString());
                    resp.put("index", IndexBootstrap.indexName());
                }
            }
        } catch (Exception e) {
            resp.put("error", e.getMessage());
        }
        sendBytes(ex, "application/json", JSON.writeValueAsBytes(resp));
    }

    private void handleEvalStream(HttpExchange ex) throws IOException {
        if (!"GET".equals(ex.getRequestMethod())) { ex.sendResponseHeaders(405, -1); return; }
        Map<String, String> params = parseQueryString(ex.getRequestURI().getQuery());

        ex.getResponseHeaders().set("Content-Type",  "text/event-stream");
        ex.getResponseHeaders().set("Cache-Control", "no-cache");
        ex.sendResponseHeaders(200, 0);

        Process proc = null;
        try (OutputStream out = ex.getResponseBody()) {
            List<String> cmd;
            try {
                cmd = buildEvalCommand(params);
            } catch (Exception e) {
                sendSse(out, "error", "Bad request: " + e.getMessage());
                return;
            }
            sendSse(out, null, "$ " + String.join(" ", cmd));

            ProcessBuilder pb = new ProcessBuilder(cmd);
            pb.directory(Path.of(EVAL_DIR).toAbsolutePath().toFile());
            pb.redirectErrorStream(true);

            try {
                proc = pb.start();
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(proc.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        sendSse(out, null, line);
                    }
                }
                int exitCode = proc.waitFor();
                sendSse(out, exitCode == 0 ? "done" : "error",
                        exitCode == 0 ? "0" : "Process exited with code " + exitCode);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                sendSse(out, "error", "Interrupted");
            }
        } finally {
            if (proc != null) proc.destroyForcibly();
        }
    }

    private void handleEvalRuns(HttpExchange ex) throws IOException {
        if (!"GET".equals(ex.getRequestMethod())) { ex.sendResponseHeaders(405, -1); return; }
        ArrayNode runs = JSON.createArrayNode();
        Path resultsDir = Path.of(RESULTS_DIR);
        if (Files.isDirectory(resultsDir)) {
            try (var dirs = Files.list(resultsDir)) {
                dirs.filter(Files::isDirectory)
                    .sorted(Comparator.reverseOrder())
                    .forEach(d -> {
                        Path scoresPath = d.resolve("ir_scores.json");
                        Path rawPath    = d.resolve("raw_results.json");
                        boolean hasMetrics = Files.exists(scoresPath);
                        boolean hasRaw     = Files.exists(rawPath);
                        if (!hasMetrics && !hasRaw) return;

                        ObjectNode run = runs.addObject()
                                .put("runId",      d.getFileName().toString())
                                .put("hasMetrics", hasMetrics)
                                .put("hasRaw",     hasRaw);
                        if (hasMetrics) {
                            try {
                                var node = JSON.readTree(scoresPath.toFile());
                                run.put("dataset",    node.path("dataset").asText(""))
                                   .put("computedAt", node.path("computed_at").asText(""));
                            } catch (Exception ignored) {}
                        }
                    });
            } catch (Exception ignored) {}
        }
        sendBytes(ex, "application/json", JSON.writeValueAsBytes(runs));
    }

    private void handleEvalResults(HttpExchange ex) throws IOException {
        if (!"GET".equals(ex.getRequestMethod())) { ex.sendResponseHeaders(405, -1); return; }
        Map<String, String> params = parseQueryString(ex.getRequestURI().getQuery());
        String runId = params.getOrDefault("runId", "").strip();

        if (isBlank(runId) || runId.contains("..") || runId.contains("/")) {
            sendBytes(ex, "application/json", JSON.writeValueAsBytes(
                    JSON.createObjectNode().put("error", "Invalid runId")));
            return;
        }
        Path scorePath = Path.of(RESULTS_DIR, runId, "ir_scores.json");
        if (!Files.exists(scorePath)) {
            sendBytes(ex, "application/json", JSON.writeValueAsBytes(
                    JSON.createObjectNode().put("error", "Run not found: " + runId)));
            return;
        }
        sendBytes(ex, "application/json", Files.readAllBytes(scorePath));
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static void sendBytes(HttpExchange ex, String contentType, byte[] body) throws IOException {
        ex.getResponseHeaders().set("Content-Type", contentType);
        ex.sendResponseHeaders(200, body.length);
        try (var out = ex.getResponseBody()) { out.write(body); }
    }

    private static void sendSse(OutputStream out, String event, String data) throws IOException {
        StringBuilder sb = new StringBuilder();
        if (event != null) sb.append("event: ").append(event).append('\n');
        // SSE data lines cannot contain newlines — split them
        for (String line : data.split("\n", -1)) {
            sb.append("data: ").append(line).append('\n');
        }
        sb.append('\n');
        out.write(sb.toString().getBytes(StandardCharsets.UTF_8));
        out.flush();
    }

    private static List<String> buildEvalCommand(Map<String, String> params) {
        String op      = params.getOrDefault("op", "");
        String dataset = params.getOrDefault("dataset", "nfcorpus");
        return switch (op) {
            case "download" -> {
                List<String> cmd = new ArrayList<>(
                        List.of("uv", "run", "searchlab-eval", "download", "--dataset", dataset));
                String slice = params.getOrDefault("slice", "");
                if (!isBlank(slice)) { cmd.add("--slice"); cmd.add(slice); }
                yield cmd;
            }
            case "ingest"  -> List.of("uv", "run", "searchlab-eval", "ingest",  "--dataset", dataset);
            case "query"   -> List.of("uv", "run", "searchlab-eval", "query",   "--dataset", dataset);
            case "metrics" -> {
                String runId = params.getOrDefault("runId", "");
                if (isBlank(runId)) throw new IllegalArgumentException("runId is required for metrics");
                yield List.of("uv", "run", "searchlab-eval", "metrics", "ir", "--run-id", runId);
            }
            default -> throw new IllegalArgumentException("Unknown op: " + op);
        };
    }

    private static Map<String, String> parseForm(String body) {
        Map<String, String> map = new HashMap<>();
        if (isBlank(body)) return map;
        for (String pair : body.split("&")) {
            String[] kv = pair.split("=", 2);
            if (kv.length == 2) map.put(
                    URLDecoder.decode(kv[0], StandardCharsets.UTF_8),
                    URLDecoder.decode(kv[1], StandardCharsets.UTF_8));
        }
        return map;
    }

    private static Map<String, String> parseQueryString(String qs) {
        return parseForm(qs == null ? "" : qs);
    }

    private static int parseInt(String s, int fallback) {
        try { return Integer.parseInt(s.strip()); } catch (NumberFormatException e) { return fallback; }
    }

    private static boolean isBlank(String s) { return s == null || s.isBlank(); }

    // ── Embedded HTML UI ─────────────────────────────────────────────────────

    private static final String HTML = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>SearchLab</title>
          <style>
            *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: system-ui, -apple-system, sans-serif; background: #f0f2f5; color: #1a1a1a; line-height: 1.5; }

            /* ── Header ── */
            header { background: #0f1117; color: #fff; padding: .75rem 2rem; display: flex; align-items: center; gap: .75rem; }
            header h1 { font-size: 1.05rem; font-weight: 600; letter-spacing: -.02em; }
            header .badge { font-size: .7rem; color: #888; background: #1e2230; padding: .15rem .5rem; border-radius: 999px; }

            /* ── Tabs ── */
            nav.tabs { background: #fff; border-bottom: 1px solid #e0e0e0; display: flex; gap: 0; padding: 0 2rem; }
            nav.tabs button {
              background: none; border: none; cursor: pointer;
              padding: .75rem 1.25rem; font-size: .85rem; font-weight: 500; color: #666;
              border-bottom: 2px solid transparent; margin-bottom: -1px;
              transition: color .15s, border-color .15s;
            }
            nav.tabs button:hover  { color: #333; }
            nav.tabs button.active { color: #4f7cff; border-bottom-color: #4f7cff; font-weight: 600; }

            /* ── Layout ── */
            .main { max-width: 960px; margin: 1.75rem auto; padding: 0 1rem; }
            .panel.hidden { display: none; }

            /* ── Cards ── */
            .card { background: #fff; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
            .card-title { font-size: .68rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #999; margin-bottom: 1rem; }

            /* ── Forms ── */
            .form-row { display: flex; gap: .75rem; flex-wrap: wrap; align-items: flex-end; }
            .field    { flex: 1 1 220px; }
            .field-sm { flex: 0 0 72px; }
            .field-xs { flex: 0 0 56px; }
            label { display: block; font-size: .72rem; font-weight: 600; color: #666; margin-bottom: .28rem; }
            input[type=text], input[type=number], select {
              width: 100%; border: 1.5px solid #d8dbe0; border-radius: 6px;
              padding: .48rem .7rem; font-size: .875rem; outline: none;
              transition: border-color .15s; background: #fff;
            }
            input:focus, select:focus { border-color: #4f7cff; }

            /* ── Buttons ── */
            .btn { background: #4f7cff; color: #fff; border: none; border-radius: 6px; padding: .52rem 1.1rem; font-size: .875rem; font-weight: 600; cursor: pointer; white-space: nowrap; transition: background .15s; }
            .btn:hover    { background: #3a68f5; }
            .btn:disabled { background: #aaa; cursor: not-allowed; }
            .btn-sm  { padding: .3rem .75rem; font-size: .78rem; }
            .btn-ghost { background: none; border: 1.5px solid #d0d3da; color: #555; }
            .btn-ghost:hover { background: #f5f5f5; }
            .btn-danger { background: #e74c3c; }
            .btn-danger:hover { background: #c0392b; }

            /* ── Alerts / banners ── */
            .alert { padding: .65rem 1rem; border-radius: 6px; font-size: .82rem; margin-bottom: 1rem; }
            .alert-warn  { background: #fffbe6; border-left: 3px solid #f0a500; color: #7a5a00; }
            .alert-error { background: #fff3f3; border-left: 3px solid #e74c3c; color: #c0392b; }
            .alert-ok    { background: #f0fff5; border-left: 3px solid #1a8c5a; color: #145c3a; }

            /* ── Spinner ── */
            .spinner { display: none; align-items: center; gap: .5rem; color: #888; font-size: .82rem; margin-top: .75rem; }
            .spinner.active { display: flex; }
            .dot { width: 5px; height: 5px; border-radius: 50%; background: #aaa; animation: bounce .9s infinite; }
            .dot:nth-child(2) { animation-delay: .2s; }
            .dot:nth-child(3) { animation-delay: .4s; }
            @keyframes bounce { 0%,80%,100%{transform:scale(0)} 40%{transform:scale(1)} }

            /* ── RAG answer ── */
            #answer-card { display: none; }
            .answer-text { white-space: pre-wrap; font-size: .875rem; background: #f8f9fb; border-radius: 6px; padding: 1rem; line-height: 1.7; }
            .sources-title { font-size: .68rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: #aaa; margin-top: 1rem; margin-bottom: .4rem; }
            .source-row { display: flex; align-items: baseline; gap: .45rem; font-size: .78rem; padding: .18rem 0; color: #555; }
            .source-rank  { color: #4f7cff; font-weight: 700; min-width: 2rem; }
            .source-score { color: #bbb; margin-left: auto; }

            /* ── Tables ── */
            table { width: 100%; border-collapse: collapse; font-size: .8rem; }
            thead th { text-align: left; padding: .4rem .65rem; background: #f4f5f7; color: #666; font-weight: 600; font-size: .72rem; white-space: nowrap; }
            thead th.sortable { cursor: pointer; user-select: none; }
            thead th.sortable:hover { background: #eaebee; }
            tbody td { padding: .38rem .65rem; border-top: 1px solid #f0f0f0; vertical-align: top; }
            tbody tr:hover td { background: #fafafa; }
            .snippet-cell { max-width: 320px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .metric-hi  { color: #1a8c5a; font-weight: 600; }
            .metric-mid { color: #b07d00; }
            .metric-lo  { color: #bbb; }
            .delta-pos  { color: #1a8c5a; }
            .delta-neg  { color: #e74c3c; }

            /* ── Log output ── */
            .log-box { background: #0f1117; color: #c8d0e0; font-family: 'SF Mono', 'Fira Mono', monospace; font-size: .75rem; border-radius: 6px; padding: .75rem 1rem; min-height: 100px; max-height: 320px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; display: none; margin-top: .75rem; }
            .log-box.active { display: block; }

            /* ── Eval controls ── */
            .op-row { display: flex; gap: .5rem; flex-wrap: wrap; margin-top: .75rem; align-items: flex-end; }
            .run-list-table { margin-top: 0; }

            /* ── Metrics controls ── */
            .metrics-control-row { display: flex; gap: .75rem; flex-wrap: wrap; align-items: flex-end; margin-bottom: 1rem; }
            .aggregate-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: .75rem; margin-bottom: 1.25rem; }
            .agg-cell { background: #f8f9fb; border-radius: 6px; padding: .65rem .75rem; text-align: center; }
            .agg-label { font-size: .65rem; color: #999; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }
            .agg-value { font-size: 1.3rem; font-weight: 700; margin-top: .15rem; }
            .filter-row { display: flex; gap: .5rem; align-items: center; margin-bottom: .5rem; }
            .filter-row input { flex: 1; }

            /* ── Responsive ── */
            @media (max-width: 600px) {
              nav.tabs { padding: 0 .5rem; overflow-x: auto; }
              nav.tabs button { padding: .65rem .75rem; font-size: .78rem; }
            }
          </style>
        </head>
        <body>

        <header>
          <h1>SearchLab</h1>
          <span class="badge">BM25 + RAG · Phase 1</span>
        </header>

        <nav class="tabs" id="tab-nav">
          <button class="active" data-tab="rag"     onclick="switchTab('rag')">RAG</button>
          <button                data-tab="query"   onclick="switchTab('query')">Query</button>
          <button                data-tab="ingest"  onclick="switchTab('ingest')">Ingest</button>
          <button                data-tab="eval"    onclick="switchTab('eval')">Eval</button>
          <button                data-tab="metrics" onclick="switchTab('metrics')">Metrics</button>
        </nav>

        <div class="main">

        <!-- ════════════════════════════════════════════ RAG ══ -->
        <div id="tab-rag" class="panel">
          <div id="api-key-warn" class="alert alert-warn" style="display:none">
            <strong>OPENAI_API_KEY not set.</strong> Start the server with the variable set to use the RAG and Ask features.
          </div>
          <div class="card">
            <div class="card-title">Ask a Question</div>
            <div class="form-row">
              <div class="field-sm" style="flex:0 0 130px">
                <label for="rag-dataset">Dataset</label>
                <select id="rag-dataset">
                  <option value="default">Default index</option>
                  <option value="nfcorpus">nfcorpus</option>
                  <option value="fiqa">FiQA-2018</option>
                </select>
              </div>
              <div class="field">
                <label for="rag-question">Question</label>
                <input type="text" id="rag-question" placeholder="e.g. what is dollar cost averaging" />
              </div>
              <div class="field-xs">
                <label for="rag-topk">Top-K</label>
                <input type="number" id="rag-topk" value="5" min="1" max="20" />
              </div>
              <div class="field">
                <label for="rag-model">Model</label>
                <input type="text" id="rag-model" value="gpt-4o-mini" />
              </div>
              <button class="btn" id="rag-btn" onclick="askRag()">Ask</button>
            </div>
            <div class="spinner" id="rag-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div> Running RAG pipeline…</div>
          </div>
          <div class="card" id="answer-card">
            <div class="card-title">Answer</div>
            <div id="answer-content"></div>
          </div>
        </div>

        <!-- ════════════════════════════════════════════ QUERY ══ -->
        <div id="tab-query" class="panel hidden">
          <div class="card">
            <div class="card-title">BM25 Search</div>
            <div class="form-row">
              <div class="field-sm" style="flex:0 0 130px">
                <label for="q-dataset">Dataset</label>
                <select id="q-dataset">
                  <option value="nfcorpus">nfcorpus</option>
                  <option value="fiqa">FiQA-2018</option>
                </select>
              </div>
              <div class="field">
                <label for="q-text">Query</label>
                <input type="text" id="q-text" placeholder="e.g. vitamin D deficiency" />
              </div>
              <div class="field-xs">
                <label for="q-topk">Top-K</label>
                <input type="number" id="q-topk" value="5" min="1" max="50" />
              </div>
              <button class="btn" id="q-btn" onclick="runQuery()">Search</button>
            </div>
            <div class="spinner" id="q-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div> Searching…</div>
          </div>
          <div class="card" id="q-results-card" style="display:none">
            <div class="card-title" id="q-results-title">Results</div>
            <div id="q-status"></div>
            <div id="q-table-wrap"></div>
          </div>
        </div>

        <!-- ════════════════════════════════════════════ INGEST ══ -->
        <div id="tab-ingest" class="panel hidden">
          <div class="card">
            <div class="card-title">Ingest PDF</div>
            <p style="font-size:.82rem;color:#666;margin-bottom:1rem">
              Indexes a PDF into the default OpenSearch index (<code>searchlab-v0</code> or <code>$SEARCHLAB_INDEX</code>).
              Enter the path relative to the project root or an absolute path.
            </p>
            <div class="form-row">
              <div class="field">
                <label for="ingest-path">PDF Path</label>
                <input type="text" id="ingest-path" placeholder="test-corpus/sample.pdf" />
              </div>
              <button class="btn" id="ingest-btn" onclick="runIngest()">Ingest</button>
            </div>
            <div class="spinner" id="ingest-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div> Ingesting…</div>
            <div id="ingest-status" style="margin-top:.75rem"></div>
          </div>
        </div>

        <!-- ════════════════════════════════════════════ EVAL ══ -->
        <div id="tab-eval" class="panel hidden">
          <div class="card">
            <div class="card-title">Eval Controls</div>
            <div class="form-row">
              <div class="field-sm" style="flex:0 0 130px">
                <label for="eval-dataset">Dataset</label>
                <select id="eval-dataset">
                  <option value="nfcorpus">nfcorpus</option>
                  <option value="fiqa">FiQA-2018</option>
                </select>
              </div>
              <div class="field-xs">
                <label for="eval-slice">Slice</label>
                <input type="number" id="eval-slice" value="100" min="1" placeholder="all" title="Limit queries for Download (optional)" />
              </div>
            </div>
            <div class="op-row">
              <button class="btn eval-op-btn" onclick="runEvalOp('download')">Download</button>
              <button class="btn eval-op-btn" onclick="runEvalOp('ingest')">Ingest</button>
              <button class="btn eval-op-btn" onclick="runEvalOp('query')">Query</button>
              <span style="flex:1"></span>
              <div class="field" style="flex:0 0 210px">
                <label for="eval-run-id">Run ID (for Metrics)</label>
                <input type="text" id="eval-run-id" placeholder="e.g. bm25_phase0" />
              </div>
              <button class="btn eval-op-btn" onclick="runEvalOp('metrics')">Compute Metrics</button>
            </div>
            <div class="log-box" id="eval-log"></div>
          </div>
          <div class="card">
            <div class="card-title" style="display:flex;justify-content:space-between;align-items:center">
              Available Runs
              <button class="btn btn-sm btn-ghost" onclick="loadEvalRuns()">Refresh</button>
            </div>
            <div id="eval-runs-content">Loading…</div>
          </div>
        </div>

        <!-- ════════════════════════════════════════════ METRICS ══ -->
        <div id="tab-metrics" class="panel hidden">
          <div class="card">
            <div class="card-title">Metrics Explorer</div>
            <div class="metrics-control-row">
              <div class="field-sm" style="flex:0 0 130px">
                <label for="m-dataset">Dataset</label>
                <select id="m-dataset" onchange="refreshRunDropdown('m-run', 'm-dataset')">
                  <option value="">All</option>
                  <option value="nfcorpus">nfcorpus</option>
                  <option value="fiqa">FiQA-2018</option>
                </select>
              </div>
              <div class="field">
                <label for="m-run">Run</label>
                <select id="m-run"><option value="">— select —</option></select>
              </div>
              <button class="btn" onclick="loadMetrics()">Load</button>
            </div>
            <div class="metrics-control-row" style="margin-bottom:0">
              <div class="field-sm" style="flex:0 0 130px">
                <label>Compare with</label>
                <select id="m-dataset2" onchange="refreshRunDropdown('m-run2', 'm-dataset2')">
                  <option value="">All</option>
                  <option value="nfcorpus">nfcorpus</option>
                  <option value="fiqa">FiQA-2018</option>
                </select>
              </div>
              <div class="field">
                <label for="m-run2">Run</label>
                <select id="m-run2"><option value="">— none —</option></select>
              </div>
              <button class="btn btn-ghost" onclick="loadCompare()">Compare</button>
            </div>
          </div>

          <div id="metrics-content" style="display:none">
            <div class="card">
              <div class="card-title" id="metrics-run-label">Aggregate Metrics</div>
              <div class="aggregate-grid" id="agg-grid"></div>
              <div class="filter-row">
                <input type="text" id="pq-filter" placeholder="Filter by query ID…" oninput="filterPerQuery()" />
                <span id="pq-count" style="font-size:.75rem;color:#aaa;white-space:nowrap"></span>
              </div>
              <table id="pq-table">
                <thead id="pq-thead"></thead>
                <tbody id="pq-tbody"></tbody>
              </table>
            </div>
          </div>
        </div>

        </div><!-- .main -->

        <script>
        // ── State ────────────────────────────────────────────────────────────
        const OPENAI_KEY_SET = __OPENAI_KEY_SET__;
        let evalRunning = false;
        let evalSource  = null;
        let allRuns     = [];
        let pqRows      = []; // current per-query data
        let pqSortCol   = 'ndcg_cut_10';
        let pqSortAsc   = false;

        const METRICS_KEYS = [
          { key: 'ndcg_cut_10', label: 'nDCG@10' },
          { key: 'ndcg_cut_5',  label: 'nDCG@5'  },
          { key: 'ndcg_cut_3',  label: 'nDCG@3'  },
          { key: 'ndcg_cut_1',  label: 'nDCG@1'  },
          { key: 'recall_10',   label: 'Recall@10'},
          { key: 'recall_5',    label: 'Recall@5' },
          { key: 'map_cut_10',  label: 'MAP@10'   },
        ];

        // ── Tab switching ────────────────────────────────────────────────────
        function switchTab(name) {
          document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
          document.querySelectorAll('#tab-nav button').forEach(b => b.classList.remove('active'));
          document.getElementById('tab-' + name).classList.remove('hidden');
          document.querySelector('[data-tab="' + name + '"]').classList.add('active');
          window.location.hash = '#' + name;
        }

        // ── Init ─────────────────────────────────────────────────────────────
        (function init() {
          if (!OPENAI_KEY_SET) document.getElementById('api-key-warn').style.display = 'block';
          const hash = window.location.hash.replace('#', '') || 'rag';
          switchTab(hash);
          loadEvalRuns();
          document.getElementById('rag-question').addEventListener('keydown', e => { if (e.key === 'Enter') askRag(); });
          document.getElementById('q-text').addEventListener('keydown', e => { if (e.key === 'Enter') runQuery(); });
        })();

        // ── Helpers ──────────────────────────────────────────────────────────
        function enc(s)    { return encodeURIComponent(s); }
        function esc(s)    { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
        function fmt(v)    { return (v == null ? '-' : v.toFixed(3)); }
        function metricCls(v) { return v >= 0.3 ? 'metric-hi' : v >= 0.15 ? 'metric-mid' : 'metric-lo'; }

        // ── RAG ──────────────────────────────────────────────────────────────
        async function askRag() {
          const question = document.getElementById('rag-question').value.trim();
          if (!question) { alert('Please enter a question.'); return; }
          const topK    = document.getElementById('rag-topk').value;
          const model   = document.getElementById('rag-model').value.trim();
          const dataset = document.getElementById('rag-dataset').value;
          const btn     = document.getElementById('rag-btn');
          btn.disabled  = true;
          document.getElementById('rag-spinner').classList.add('active');
          document.getElementById('answer-card').style.display = 'none';
          try {
            const r = await fetch('/rag', {
              method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: `question=${enc(question)}&topK=${topK}&model=${enc(model)}&dataset=${enc(dataset)}`
            });
            renderAnswer(await r.json());
          } catch (e) { renderAnswer({ error: 'Network error: ' + e.message }); }
          finally {
            btn.disabled = false;
            document.getElementById('rag-spinner').classList.remove('active');
          }
        }

        function renderAnswer(data) {
          const card = document.getElementById('answer-card');
          const el   = document.getElementById('answer-content');
          card.style.display = 'block';
          if (data.error) {
            el.innerHTML = `<div class="alert alert-error">${esc(data.error)}</div>`;
            return;
          }
          const indexLabel = data.index ? `<span style="font-size:.7rem;color:#aaa;font-weight:400"> · index: ${esc(data.index)}</span>` : '';
          document.querySelector('#answer-card .card-title').innerHTML = 'Answer' + indexLabel;
          let html = `<div class="answer-text">${esc(data.answer)}</div>`;
          if (data.sources && data.sources.length) {
            html += '<div class="sources-title">Sources</div>';
            data.sources.forEach(s => {
              html += `<div class="source-row">
                <span class="source-rank">[${s.rank}]</span>
                <span>${esc(s.filename)}</span>
                <span style="color:#ddd">·</span>
                <span>p.${s.page}</span>
                <span class="source-score">score ${s.score.toFixed(3)}</span>
              </div>`;
            });
          }
          el.innerHTML = html;
        }

        // ── BM25 Query ───────────────────────────────────────────────────────
        async function runQuery() {
          const q       = document.getElementById('q-text').value.trim();
          const topK    = document.getElementById('q-topk').value;
          const dataset = document.getElementById('q-dataset').value;
          if (!q) { alert('Please enter a query.'); return; }
          const btn = document.getElementById('q-btn');
          btn.disabled = true;
          document.getElementById('q-spinner').classList.add('active');
          document.getElementById('q-results-card').style.display = 'none';
          try {
            const r = await fetch('/api/query', {
              method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: `query=${enc(q)}&topK=${topK}&dataset=${enc(dataset)}`
            });
            renderQueryResults(await r.json(), dataset);
          } catch(e) { renderQueryResults({ error: e.message }, dataset); }
          finally { btn.disabled = false; document.getElementById('q-spinner').classList.remove('active'); }
        }

        function renderQueryResults(data, dataset) {
          const card = document.getElementById('q-results-card');
          card.style.display = 'block';
          const statusEl = document.getElementById('q-status');
          const tableEl  = document.getElementById('q-table-wrap');
          if (data.error) {
            statusEl.innerHTML = `<div class="alert alert-error">${esc(data.error)}</div>`;
            tableEl.innerHTML = '';
            return;
          }
          statusEl.innerHTML = '';
          document.getElementById('q-results-title').textContent =
            `Results — ${data.hits.length} hit${data.hits.length !== 1 ? 's' : ''} · index: ${data.index}`;
          if (!data.hits.length) {
            tableEl.innerHTML = '<p style="font-size:.82rem;color:#aaa;padding:.5rem 0">No results found.</p>';
            return;
          }
          tableEl.innerHTML = `<table>
            <thead><tr>
              <th style="width:3rem">Rank</th>
              <th style="width:5rem">Score</th>
              <th>Source</th>
              <th style="width:3.5rem">Page</th>
              <th>Snippet</th>
            </tr></thead>
            <tbody>
              ${data.hits.map(h => `<tr>
                <td>${h.rank}</td>
                <td>${h.score.toFixed(4)}</td>
                <td>${esc(h.filename)}</td>
                <td>${h.page}</td>
                <td class="snippet-cell" title="${esc(h.snippet)}">${esc(h.snippet)}</td>
              </tr>`).join('')}
            </tbody>
          </table>`;
        }

        // ── Ingest ───────────────────────────────────────────────────────────
        async function runIngest() {
          const path = document.getElementById('ingest-path').value.trim();
          if (!path) { alert('Please enter a PDF path.'); return; }
          const btn = document.getElementById('ingest-btn');
          btn.disabled = true;
          document.getElementById('ingest-spinner').classList.add('active');
          document.getElementById('ingest-status').innerHTML = '';
          try {
            const r = await fetch('/api/ingest', {
              method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: `pdfPath=${enc(path)}`
            });
            const data = await r.json();
            const statusEl = document.getElementById('ingest-status');
            if (data.error) {
              statusEl.innerHTML = `<div class="alert alert-error">${esc(data.error)}</div>`;
            } else {
              statusEl.innerHTML = `<div class="alert alert-ok">
                Indexed <strong>${data.chunksIndexed}</strong> chunks from
                <strong>${esc(data.filename)}</strong> into index <code>${esc(data.index)}</code>.
              </div>`;
            }
          } catch(e) {
            document.getElementById('ingest-status').innerHTML =
              `<div class="alert alert-error">Network error: ${esc(e.message)}</div>`;
          } finally {
            btn.disabled = false;
            document.getElementById('ingest-spinner').classList.remove('active');
          }
        }

        // ── Eval ─────────────────────────────────────────────────────────────
        function setEvalBtns(disabled) {
          evalRunning = disabled;
          document.querySelectorAll('.eval-op-btn').forEach(b => b.disabled = disabled);
        }

        function runEvalOp(op) {
          if (evalRunning) return;
          const dataset = document.getElementById('eval-dataset').value;
          const slice   = document.getElementById('eval-slice').value.trim();
          const runId   = document.getElementById('eval-run-id').value.trim();

          const log = document.getElementById('eval-log');
          log.textContent = '';
          log.classList.add('active');

          let url = `/api/eval/stream?op=${enc(op)}&dataset=${enc(dataset)}`;
          if (op === 'download' && slice) url += `&slice=${enc(slice)}`;
          if (op === 'metrics')           url += `&runId=${enc(runId)}`;

          if (evalSource) evalSource.close();
          setEvalBtns(true);

          evalSource = new EventSource(url);

          evalSource.onmessage = e => {
            log.textContent += e.data + '\\n';
            log.scrollTop = log.scrollHeight;
          };

          evalSource.addEventListener('done', () => {
            log.textContent += '\\n✓ Done\\n';
            evalSource.close();
            evalSource = null;
            setEvalBtns(false);
            if (op === 'query') autoDetectLatestRun(dataset);
            loadEvalRuns();
          });

          evalSource.addEventListener('error', e => {
            const msg = e.data || 'Stream error';
            log.textContent += '\\n✗ ' + msg + '\\n';
            evalSource.close();
            evalSource = null;
            setEvalBtns(false);
          });

          // Guard against onerror (connection refused, etc.)
          evalSource.onerror = () => {
            if (evalSource.readyState === 2) { // CLOSED
              log.textContent += '\\n✗ Connection lost.\\n';
              setEvalBtns(false);
              evalSource = null;
            }
          };
        }

        async function autoDetectLatestRun(dataset) {
          await loadEvalRuns();
          const rawOnly = allRuns.filter(r => r.hasRaw && !r.hasMetrics && (r.dataset === dataset || !r.dataset));
          if (rawOnly.length) {
            document.getElementById('eval-run-id').value = rawOnly[0].runId;
          }
        }

        async function loadEvalRuns() {
          try {
            const r = await fetch('/api/eval/runs');
            allRuns = await r.json();
            renderEvalRuns(allRuns);
            // refresh metrics dropdowns
            refreshRunDropdown('m-run',  'm-dataset');
            refreshRunDropdown('m-run2', 'm-dataset2');
          } catch(e) {
            document.getElementById('eval-runs-content').innerHTML =
              `<div class="alert alert-error">Could not load runs: ${esc(e.message)}</div>`;
          }
        }

        function renderEvalRuns(runs) {
          const el = document.getElementById('eval-runs-content');
          if (!runs.length) {
            el.innerHTML = '<p style="font-size:.82rem;color:#aaa">No eval runs found in searchlab-eval/results/</p>';
            return;
          }
          el.innerHTML = `<table class="run-list-table">
            <thead><tr><th>Run ID</th><th>Dataset</th><th>Computed At</th><th>Has Metrics</th><th></th></tr></thead>
            <tbody>
              ${runs.map(r => `<tr>
                <td><code>${esc(r.runId)}</code></td>
                <td>${esc(r.dataset || '—')}</td>
                <td style="font-size:.72rem;color:#888">${esc(r.computedAt ? r.computedAt.slice(0,19).replace('T',' ') : '—')}</td>
                <td>${r.hasMetrics ? '✓' : '<span style="color:#ccc">—</span>'}</td>
                <td>
                  ${r.hasMetrics
                    ? `<button class="btn btn-sm btn-ghost" onclick="viewRunMetrics('${esc(r.runId)}')">View</button>`
                    : (r.hasRaw
                      ? `<button class="btn btn-sm btn-ghost" onclick="prefillMetricsRun('${esc(r.runId)}')">Compute</button>`
                      : '')}
                </td>
              </tr>`).join('')}
            </tbody>
          </table>`;
        }

        function prefillMetricsRun(runId) {
          document.getElementById('eval-run-id').value = runId;
        }

        function viewRunMetrics(runId) {
          switchTab('metrics');
          // find the run and pre-select its dropdowns
          const run = allRuns.find(r => r.runId === runId);
          if (run && run.dataset) {
            document.getElementById('m-dataset').value = run.dataset === 'nfcorpus' ? 'nfcorpus' : 'fiqa';
            refreshRunDropdown('m-run', 'm-dataset');
          }
          document.getElementById('m-run').value = runId;
          loadMetrics();
        }

        // ── Metrics ──────────────────────────────────────────────────────────
        function refreshRunDropdown(dropId, datasetDropId) {
          const datasetFilter = document.getElementById(datasetDropId).value;
          const drop = document.getElementById(dropId);
          const prev = drop.value;
          drop.innerHTML = '<option value="">— select —</option>';
          allRuns.filter(r => r.hasMetrics && (!datasetFilter || r.dataset === datasetFilter))
                 .forEach(r => {
                   const opt = document.createElement('option');
                   opt.value = r.runId;
                   opt.textContent = r.runId + (r.computedAt ? '  (' + r.computedAt.slice(0,10) + ')' : '');
                   drop.appendChild(opt);
                 });
          if (prev) drop.value = prev;
        }

        async function loadMetrics() {
          const runId = document.getElementById('m-run').value;
          if (!runId) { alert('Please select a run.'); return; }
          try {
            const r = await fetch(`/api/eval/results?runId=${enc(runId)}`);
            const data = await r.json();
            if (data.error) { alert(data.error); return; }
            renderMetrics(data, null);
          } catch(e) { alert('Error loading metrics: ' + e.message); }
        }

        async function loadCompare() {
          const runId1 = document.getElementById('m-run').value;
          const runId2 = document.getElementById('m-run2').value;
          if (!runId1) { alert('Please select a primary run.'); return; }
          if (!runId2 || runId2 === runId1) { loadMetrics(); return; }
          try {
            const [r1, r2] = await Promise.all([
              fetch(`/api/eval/results?runId=${enc(runId1)}`).then(r => r.json()),
              fetch(`/api/eval/results?runId=${enc(runId2)}`).then(r => r.json()),
            ]);
            if (r1.error || r2.error) { alert(r1.error || r2.error); return; }
            renderMetrics(r1, r2);
          } catch(e) { alert('Error: ' + e.message); }
        }

        function renderMetrics(data1, data2) {
          document.getElementById('metrics-content').style.display = 'block';
          const run2Id = data2 ? document.getElementById('m-run2').value : null;
          document.getElementById('metrics-run-label').textContent =
            data1.run_id + (run2Id ? ' vs ' + run2Id : '') +
            ' — ' + (data1.dataset || '') +
            (data1.computed_at ? ' · ' + data1.computed_at.slice(0,10) : '');

          renderAggregate(data1.aggregate || {}, data2 ? data2.aggregate || {} : null);
          buildPerQueryData(data1.per_query || {}, data2 ? data2.per_query || {} : null);
          renderPerQuery();
        }

        function renderAggregate(agg1, agg2) {
          const grid = document.getElementById('agg-grid');
          grid.innerHTML = METRICS_KEYS.map(m => {
            const v1 = agg1[m.key] ?? 0;
            const v2 = agg2 ? (agg2[m.key] ?? 0) : null;
            const delta = v2 != null ? v2 - v1 : null;
            const deltaStr = delta != null
              ? `<div style="font-size:.7rem;margin-top:.1rem" class="${delta >= 0 ? 'delta-pos' : 'delta-neg'}">${delta >= 0 ? '+' : ''}${delta.toFixed(3)}</div>`
              : '';
            return `<div class="agg-cell">
              <div class="agg-label">${m.label}</div>
              <div class="agg-value ${metricCls(v1)}">${v1.toFixed(3)}</div>
              ${v2 != null ? `<div style="font-size:.8rem;color:#888">${v2.toFixed(3)}</div>` : ''}
              ${deltaStr}
            </div>`;
          }).join('');
        }

        function buildPerQueryData(pq1, pq2) {
          const keys = Object.keys(pq1);
          pqRows = keys.map(qid => {
            const r1 = pq1[qid] || {};
            const r2 = pq2 ? (pq2[qid] || {}) : null;
            return { qid, r1, r2 };
          });
        }

        function sortPQ(col) {
          if (pqSortCol === col) pqSortAsc = !pqSortAsc;
          else { pqSortCol = col; pqSortAsc = false; }
          renderPerQuery();
        }

        function filterPerQuery() {
          renderPerQuery();
        }

        function renderPerQuery() {
          const filter = (document.getElementById('pq-filter').value || '').toLowerCase();
          const visible = pqRows.filter(r => !filter || r.qid.toLowerCase().includes(filter));
          const sorted  = [...visible].sort((a, b) => {
            const va = a.r1[pqSortCol] ?? 0;
            const vb = b.r1[pqSortCol] ?? 0;
            return pqSortAsc ? va - vb : vb - va;
          });

          const hasCompare = pqRows.length && pqRows[0].r2 != null;
          document.getElementById('pq-count').textContent = `${visible.length} / ${pqRows.length} queries`;

          const thSort = key => {
            const arrow = pqSortCol === key ? (pqSortAsc ? ' ▲' : ' ▼') : '';
            return `<th class="sortable" onclick="sortPQ('${key}')">${METRICS_KEYS.find(m=>m.key===key)?.label || key}${arrow}</th>`;
          };

          document.getElementById('pq-thead').innerHTML = `<tr>
            <th>Query ID</th>
            ${METRICS_KEYS.map(m => thSort(m.key)).join('')}
            ${hasCompare ? '<th colspan="' + METRICS_KEYS.length + '" style="background:#f0f8ff;color:#4f7cff">Δ (run2 − run1)</th>' : ''}
          </tr>`;

          document.getElementById('pq-tbody').innerHTML = sorted.map(({qid, r1, r2}) => {
            const cells1 = METRICS_KEYS.map(m => {
              const v = r1[m.key] ?? 0;
              return `<td class="${metricCls(v)}">${v.toFixed(3)}</td>`;
            }).join('');
            const cells2 = hasCompare ? METRICS_KEYS.map(m => {
              const d = (r2[m.key] ?? 0) - (r1[m.key] ?? 0);
              return `<td class="${d > 0.001 ? 'delta-pos' : d < -0.001 ? 'delta-neg' : 'metric-lo'}" style="background:#f8fbff">${d >= 0 ? '+' : ''}${d.toFixed(3)}</td>`;
            }).join('') : '';
            return `<tr><td><code>${esc(qid)}</code></td>${cells1}${cells2}</tr>`;
          }).join('');
        }
        </script>
        </body>
        </html>
        """;
}
