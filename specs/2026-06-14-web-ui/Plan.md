# Plan — Web UI (Full Feature Parity)

**Scope:** Extend `WebCommand.java` (the existing `./searchlab serve`) with a multi-section UI that covers every CLI feature. No changes to domain logic — only new HTTP routes in `WebCommand` and new HTML/JS inside the embedded `HTML` string.

**Datasets in scope:** nfcorpus, FiQA-2018

**Approach for long-running eval commands:** Server-Sent Events (SSE). The browser opens an event stream; the server pipes subprocess stdout/stderr line-by-line. No polling, no timeouts on the HTTP layer.

---

## Group 1 — Navigation & Layout

**1.1** Replace the single-page layout with a tab-based shell:
- Tabs: **RAG** | **Query** | **Ingest** | **Eval** | **Metrics**
- Active tab persists in the URL hash (`#rag`, `#query`, etc.) so refresh keeps position.
- Header stays as-is; only the content area changes.

**1.2** Extend the RAG section with a **dataset selector** (nfcorpus | FiQA-2018 | Default index) so the BM25 retrieval step queries the correct OpenSearch index before calling the LLM. The `/rag` handler performs the search inline against the selected index rather than delegating to `RagCommand.execute()`, which is index-agnostic.

**1.3** Keep the existing eval aggregate table — move it into the **Metrics** tab (not the landing tab).

---

## Group 2 — BM25 Query UI

New route: `POST /api/query`

**2.1** Add `POST /api/query` to `WebCommand`:
- Reads `question` and `topK` from form body.
- Calls `Bm25Searcher` directly (same pattern as `RagCommand.execute` — no subprocess).
- Returns JSON: `{ hits: [{ rank, filename, page, score, snippet }] }`
- Returns `{ error: "..." }` on failure.

**2.2** Add **Query** tab content:
- Text input for the search query.
- Top-K number input (default 5).
- Dataset selector: nfcorpus | FiQA-2018 (passes index name to searcher).
- "Search" button → POST to `/api/query`.
- Results rendered as a table: Rank | Score | Source | Page | Snippet (200 chars).

> **Note:** `Bm25Searcher` currently uses a single fixed index. Group 2 must pass the selected index name through. This is plumbing in `WebCommand` only — `Bm25Searcher.search(question, topK, indexName)` already exists or the index is set per-client construction. No logic change needed.

---

## Group 3 — Ingest UI

New route: `POST /api/ingest`

**3.1** Add `POST /api/ingest` to `WebCommand`:
- Reads `pdfPath` (relative or absolute) from form body.
- Calls `Indexer`/`IngestCommand` logic directly (same in-process call pattern).
- Returns JSON: `{ chunksIndexed: N, filename: "..." }` or `{ error: "..." }`.

**3.2** Add **Ingest** tab content:
- Text input: path to PDF (e.g. `test-corpus/sample.pdf` or absolute).
- Dataset / index target selector: nfcorpus index | FiQA index | default index.
- "Ingest" button → POST to `/api/ingest`.
- Result: green success banner (`Indexed N chunks from filename`) or red error.
- Show timestamp of last ingest per index.

---

## Group 4 — Eval Controls UI (Download · Ingest · Query · Metrics)

New routes (all SSE-streaming):
- `GET /api/eval/stream?op=download&dataset=nfcorpus&slice=100`
- `GET /api/eval/stream?op=ingest&dataset=nfcorpus`
- `GET /api/eval/stream?op=query&dataset=nfcorpus`
- `GET /api/eval/stream?op=metrics&runId=<id>`

**4.1** Add a single `/api/eval/stream` SSE endpoint to `WebCommand`:
- Reads `op`, `dataset`, `slice`, `runId` from query params.
- Builds the appropriate `uv run searchlab-eval <op> ...` command.
- Runs it as a `ProcessBuilder` with working directory `searchlab-eval/`.
- Pipes each stdout/stderr line as an SSE `data:` event.
- Sends a final `event: done` (exit code 0) or `event: error` (non-zero).
- Content-Type: `text/event-stream`.

**4.2** Add `/api/eval/runs` GET endpoint:
- Scans `searchlab-eval/results/` for directories containing `ir_scores.json`.
- Returns JSON: `[{ runId, dataset, computedAt }]` sorted by date descending.

**4.3** Add **Eval** tab content:

```
Dataset:  [ nfcorpus ▾ ]   Slice: [ 100 ]

[ Download ]  [ Ingest ]  [ Query ]  [ Compute Metrics ]

─── Output ──────────────────────────────────────────────
(SSE log stream appears here, line by line)
─────────────────────────────────────────────────────────

Available runs:
  bm25_phase0          nfcorpus    2026-06-08   [ View Metrics ]
  fiqa-bm25-phase0     fiqa        2026-06-08   [ View Metrics ]
  my-test-run          nfcorpus    2026-06-08   [ View Metrics ]
```

- Each button opens the SSE stream and appends lines to the output log area.
- Only one operation runs at a time (others disabled while streaming).
- "Slice" field applies only to Download.
- "Compute Metrics" uses the most recent `raw_results.json` run ID auto-detected for the selected dataset, or lets the user type a run ID.

---

## Group 5 — Metrics Dashboard

New route: `GET /api/eval/results/:runId`

**5.1** Add `/api/eval/results` GET:
- Already covered by Group 4.2.

**5.2** Add `/api/eval/results/:runId` GET:
- Reads `searchlab-eval/results/<runId>/ir_scores.json`.
- Returns full JSON (aggregate + per_query).

**5.3** Add **Metrics** tab content:

```
Dataset:  [ nfcorpus ▾ ]     Run:  [ bm25_phase0 ▾ ]   [ Load ]

── Aggregate ────────────────────────────────────────────
  nDCG@10   nDCG@5   nDCG@3   nDCG@1   Recall@10  Recall@5  MAP@10
   0.328     0.360    0.394    0.460     0.140      0.117     0.122

── Per-query (click column header to sort) ──────────────
  Query ID      Recall@10   nDCG@10   MAP@10   ▲▼
  PLAIN-1039    1.000       1.000     1.000
  PLAIN-1130    1.000       1.000     1.000
  ...
  PLAIN-1008    0.000       0.000     0.000
```

- Aggregate row: colour-coded (green ≥ 0.3, amber ≥ 0.15, grey below).
- Per-query table: client-side sortable by any column; default sort by nDCG@10 descending.
- Dataset dropdown: nfcorpus | FiQA-2018.
- Run dropdown: populated from `/api/eval/runs`, filtered to the selected dataset.
- Side-by-side comparison: "Compare with…" second run selector → adds a Δ column.

---

## Group 6 — Polish & Error States

**6.1** Every action button shows a spinner while in-flight; disabled while another op is running.

**6.2** Every error (subprocess non-zero, OpenSearch down, missing API key) surfaces in a red banner with the full message — no raw stack traces.

**6.3** `OPENAI_API_KEY` absent → RAG "Ask" button shows a yellow warning instead of silently failing on click.

**6.4** Responsive layout: tabs collapse to a top-aligned list on narrow viewports.

---

## Definition of Done

- [ ] All five tabs render without errors
- [ ] Query tab returns BM25 hits for both nfcorpus and FiQA
- [ ] Ingest tab indexes a PDF and reports chunk count
- [ ] Eval tab can run download → ingest → query → metrics end-to-end with live log output
- [ ] Metrics tab loads aggregate + per-query data, sorts correctly, colour codes metrics
- [ ] All error scenarios surface a human-readable message
- [ ] `mvn package` still produces a single fat JAR; no new runtime dependencies added
- [ ] All existing unit tests still pass
