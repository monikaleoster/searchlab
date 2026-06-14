package com.searchlab.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.searchlab.rag.RagResult;
import com.searchlab.search.SearchHit;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;

@Command(name = "serve", description = "Launch a local web UI for RAG queries and eval reports")
public class WebCommand implements Callable<Integer> {

    @Option(names = "--port", defaultValue = "8080",
            description = "Port to listen on (default: ${DEFAULT-VALUE})")
    private int port;

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String[] EVAL_FILES = {
        "searchlab-eval/results/bm25_phase0/ir_scores.json",
        "searchlab-eval/results/fiqa-bm25-phase0/ir_scores.json"
    };

    @Override
    public Integer call() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/",    this::handleRoot);
        server.createContext("/rag", this::handleRag);
        server.createContext("/eval", this::handleEval);
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
        sendBytes(ex, "text/html; charset=utf-8", HTML.getBytes(StandardCharsets.UTF_8));
    }

    private void handleRag(HttpExchange ex) throws IOException {
        if (!"POST".equals(ex.getRequestMethod())) { ex.sendResponseHeaders(405, -1); return; }

        Map<String, String> params = parseForm(
                new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));

        String question = params.getOrDefault("question", "").strip();
        int    topK     = parseInt(params.getOrDefault("topK", "5"), 5);
        String model    = params.getOrDefault("model", "").strip();

        RagResult result = RagCommand.execute(question, topK, RagCommand.resolveModel(model.isEmpty() ? null : model));

        ObjectNode resp = JSON.createObjectNode();
        if (result.error() != null) {
            resp.put("error", result.error());
        } else {
            resp.put("answer", result.answer());
            ArrayNode sources = resp.putArray("sources");
            for (SearchHit hit : result.sources()) {
                sources.addObject()
                       .put("rank",     hit.rank())
                       .put("filename", hit.sourceFilename())
                       .put("page",     hit.pageNumber())
                       .put("score",    hit.score());
            }
        }
        sendBytes(ex, "application/json", JSON.writeValueAsBytes(resp));
    }

    private void handleEval(HttpExchange ex) throws IOException {
        if (!"GET".equals(ex.getRequestMethod())) { ex.sendResponseHeaders(405, -1); return; }

        ObjectNode resp = JSON.createObjectNode();
        for (String path : EVAL_FILES) {
            Path p = Path.of(path);
            if (Files.exists(p)) {
                try {
                    var node = JSON.readTree(p.toFile());
                    String dataset = node.path("dataset").asText(p.getFileName().toString());
                    resp.set(dataset, node);
                } catch (Exception ignored) {}
            }
        }
        sendBytes(ex, "application/json", JSON.writeValueAsBytes(resp));
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static void sendBytes(HttpExchange ex, String contentType, byte[] body) throws IOException {
        ex.getResponseHeaders().set("Content-Type", contentType);
        ex.sendResponseHeaders(200, body.length);
        try (var out = ex.getResponseBody()) { out.write(body); }
    }

    private static Map<String, String> parseForm(String body) {
        Map<String, String> map = new HashMap<>();
        for (String pair : body.split("&")) {
            String[] kv = pair.split("=", 2);
            if (kv.length == 2) {
                map.put(URLDecoder.decode(kv[0], StandardCharsets.UTF_8),
                        URLDecoder.decode(kv[1], StandardCharsets.UTF_8));
            }
        }
        return map;
    }

    private static int parseInt(String s, int fallback) {
        try { return Integer.parseInt(s.strip()); } catch (NumberFormatException e) { return fallback; }
    }

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
            body {
              font-family: system-ui, -apple-system, sans-serif;
              background: #f0f2f5;
              color: #1a1a1a;
              line-height: 1.5;
            }
            header {
              background: #0f1117;
              color: #fff;
              padding: 1rem 2rem;
              display: flex;
              align-items: center;
              gap: .75rem;
            }
            header h1 { font-size: 1.1rem; font-weight: 600; letter-spacing: -.02em; }
            header span { font-size: .75rem; color: #888; background: #1e2230;
                          padding: .15rem .5rem; border-radius: 999px; }
            .main { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }

            .card {
              background: #fff;
              border-radius: 10px;
              padding: 1.5rem;
              margin-bottom: 1.5rem;
              box-shadow: 0 1px 4px rgba(0,0,0,.08);
            }
            .card-title {
              font-size: .7rem;
              font-weight: 700;
              letter-spacing: .08em;
              text-transform: uppercase;
              color: #888;
              margin-bottom: 1rem;
            }

            .form-row { display: flex; gap: .75rem; flex-wrap: wrap; align-items: flex-end; }
            .field     { flex: 1 1 240px; }
            .field-sm  { flex: 0 0 72px; }
            label { display: block; font-size: .75rem; font-weight: 600; color: #555; margin-bottom: .3rem; }
            input[type=text], input[type=number] {
              width: 100%;
              border: 1.5px solid #d8dbe0;
              border-radius: 6px;
              padding: .5rem .75rem;
              font-size: .9rem;
              outline: none;
              transition: border-color .15s;
            }
            input:focus { border-color: #4f7cff; }

            .btn {
              background: #4f7cff;
              color: #fff;
              border: none;
              border-radius: 6px;
              padding: .55rem 1.25rem;
              font-size: .9rem;
              font-weight: 600;
              cursor: pointer;
              white-space: nowrap;
              transition: background .15s;
            }
            .btn:hover   { background: #3a68f5; }
            .btn:disabled { background: #aaa; cursor: not-allowed; }

            .spinner { display: none; align-items: center; gap: .5rem; color: #888; font-size: .85rem; margin-top: .75rem; }
            .spinner.active { display: flex; }
            .dot { width: 6px; height: 6px; border-radius: 50%; background: #aaa; animation: bounce .9s infinite; }
            .dot:nth-child(2) { animation-delay: .2s; }
            .dot:nth-child(3) { animation-delay: .4s; }
            @keyframes bounce { 0%,80%,100%{transform:scale(0)} 40%{transform:scale(1)} }

            #answer-card { display: none; }
            .answer-text {
              white-space: pre-wrap;
              font-size: .9rem;
              background: #f8f9fb;
              border-radius: 6px;
              padding: 1rem;
              line-height: 1.7;
            }
            .error-box {
              background: #fff3f3;
              border-left: 3px solid #e74c3c;
              padding: .75rem 1rem;
              border-radius: 4px;
              color: #c0392b;
              font-size: .875rem;
            }
            .sources-title {
              font-size: .75rem;
              font-weight: 700;
              letter-spacing: .06em;
              text-transform: uppercase;
              color: #999;
              margin-top: 1.25rem;
              margin-bottom: .5rem;
            }
            .source-row {
              display: flex;
              align-items: baseline;
              gap: .5rem;
              font-size: .8rem;
              padding: .2rem 0;
              color: #444;
            }
            .source-rank  { color: #4f7cff; font-weight: 700; min-width: 2rem; }
            .source-score { color: #aaa; margin-left: auto; }

            /* Eval table */
            .eval-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
            @media (max-width: 600px) { .eval-grid { grid-template-columns: 1fr; } }
            .eval-dataset { font-size: .75rem; font-weight: 700; color: #555; margin-bottom: .5rem; }
            table { width: 100%; border-collapse: collapse; font-size: .82rem; }
            thead th {
              text-align: left;
              padding: .35rem .6rem;
              background: #f4f5f7;
              color: #666;
              font-weight: 600;
              font-size: .72rem;
            }
            tbody td { padding: .35rem .6rem; border-top: 1px solid #f0f0f0; }
            .metric-hi  { color: #1a8c5a; font-weight: 600; }
            .metric-mid { color: #b07d00; }
            .metric-lo  { color: #888; }
          </style>
        </head>
        <body>

        <header>
          <h1>SearchLab</h1>
          <span>BM25 + RAG · Phase 1</span>
        </header>

        <div class="main">

          <!-- ── Query card ───────────────────────────── -->
          <div class="card">
            <div class="card-title">Ask a question</div>
            <div class="form-row">
              <div class="field">
                <label for="question">Question</label>
                <input type="text" id="question"
                       placeholder="e.g. what is dollar cost averaging" />
              </div>
              <div class="field-sm">
                <label for="topk">Top-K</label>
                <input type="number" id="topk" value="5" min="1" max="20" />
              </div>
              <div class="field">
                <label for="model">Model</label>
                <input type="text" id="model" value="gpt-4o-mini" />
              </div>
              <button class="btn" id="ask-btn" onclick="askRag()">Ask</button>
            </div>
            <div class="spinner" id="spinner">
              <div class="dot"></div><div class="dot"></div><div class="dot"></div>
              Running RAG pipeline…
            </div>
          </div>

          <!-- ── Answer card ─────────────────────────── -->
          <div class="card" id="answer-card">
            <div class="card-title">Answer</div>
            <div id="answer-content"></div>
          </div>

          <!-- ── Eval card ───────────────────────────── -->
          <div class="card">
            <div class="card-title">IR Evaluation — BM25 Phase 0</div>
            <div class="eval-grid" id="eval-grid">
              <div style="color:#aaa;font-size:.85rem">Loading eval reports…</div>
            </div>
          </div>

        </div>

        <script>
        // ── RAG ──────────────────────────────────────────────────────────────

        async function askRag() {
          const question = document.getElementById('question').value.trim();
          if (!question) { alert('Please enter a question.'); return; }

          const topK  = document.getElementById('topk').value;
          const model = document.getElementById('model').value.trim();
          const btn   = document.getElementById('ask-btn');

          btn.disabled = true;
          document.getElementById('spinner').classList.add('active');
          document.getElementById('answer-card').style.display = 'none';

          try {
            const resp = await fetch('/rag', {
              method: 'POST',
              headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: `question=${enc(question)}&topK=${topK}&model=${enc(model)}`
            });
            renderAnswer(await resp.json());
          } catch (e) {
            renderAnswer({ error: 'Network error: ' + e.message });
          } finally {
            btn.disabled = false;
            document.getElementById('spinner').classList.remove('active');
          }
        }

        function enc(s) { return encodeURIComponent(s); }

        function renderAnswer(data) {
          const card    = document.getElementById('answer-card');
          const content = document.getElementById('answer-content');
          card.style.display = 'block';

          if (data.error) {
            content.innerHTML = `<div class="error-box">${escHtml(data.error)}</div>`;
            return;
          }

          let html = `<div class="answer-text">${escHtml(data.answer)}</div>`;

          if (data.sources && data.sources.length) {
            html += '<div class="sources-title">Sources</div>';
            data.sources.forEach(s => {
              html += `<div class="source-row">
                <span class="source-rank">[${s.rank}]</span>
                <span>${escHtml(s.filename)}</span>
                <span style="color:#bbb">·</span>
                <span>p. ${s.page}</span>
                <span class="source-score">score ${s.score.toFixed(3)}</span>
              </div>`;
            });
          }

          content.innerHTML = html;
        }

        function escHtml(s) {
          return String(s)
            .replace(/&/g,'&amp;').replace(/</g,'&lt;')
            .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        document.getElementById('question').addEventListener('keydown', e => {
          if (e.key === 'Enter') askRag();
        });

        // ── Eval ─────────────────────────────────────────────────────────────

        const METRICS = [
          { key: 'ndcg_cut_10', label: 'nDCG@10' },
          { key: 'ndcg_cut_5',  label: 'nDCG@5'  },
          { key: 'ndcg_cut_3',  label: 'nDCG@3'  },
          { key: 'recall_10',   label: 'Recall@10'},
          { key: 'recall_5',    label: 'Recall@5' },
          { key: 'map_cut_10',  label: 'MAP@10'   },
        ];

        function metricClass(v) {
          return v >= 0.3 ? 'metric-hi' : v >= 0.15 ? 'metric-mid' : 'metric-lo';
        }

        function evalTable(dataset, agg) {
          let rows = METRICS.map(m => {
            const v = agg[m.key] ?? 0;
            return `<tr>
              <td>${m.label}</td>
              <td class="${metricClass(v)}">${v.toFixed(3)}</td>
            </tr>`;
          }).join('');

          return `<div>
            <div class="eval-dataset">${escHtml(dataset)}</div>
            <table>
              <thead><tr><th>Metric</th><th>Score</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>`;
        }

        async function loadEval() {
          try {
            const resp = await fetch('/eval');
            const data = await resp.json();
            const grid = document.getElementById('eval-grid');
            const keys = Object.keys(data);
            if (keys.length === 0) {
              grid.innerHTML = '<div style="color:#aaa;font-size:.85rem">No eval files found in searchlab-eval/results/</div>';
              return;
            }
            grid.innerHTML = keys.map(k => {
              const node = data[k];
              return evalTable(
                node.dataset ?? k,
                node.aggregate ?? {}
              );
            }).join('');
          } catch (e) {
            document.getElementById('eval-grid').innerHTML =
              '<div style="color:#c0392b;font-size:.85rem">Could not load eval data.</div>';
          }
        }

        loadEval();
        </script>
        </body>
        </html>
        """;
}
