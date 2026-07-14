# Plan — Phase 2: RAG Evaluation

**Companion to:** `requirements.md`

Each group is a logical unit of work. Complete groups in order — later groups depend on earlier ones being runnable.

---

## Group 1 — Dependency

1.1 Move `ragas>=0.2` from `[project.optional-dependencies]` to `[project.dependencies]` in `searchlab-eval/pyproject.toml`. Run `uv sync` to install it.

1.2 Add `SEARCHLAB_LLM_JUDGE_MODEL` to `.env.example` with value `gpt-4o-mini` and an inline comment: `# Model used by RAGAS as the LLM judge (separate from SEARCHLAB_LLM_MODEL which generates answers)`.

1.3 Confirm `uv run searchlab-eval --help` still lists all existing subcommands without error.

---

## Group 2 — RAG Results Generation

Create `searchlab-eval/searchlab_eval/rag_runner.py`.

2.1 Write `retrieve_contexts(query_text, opensearch_url, index, top_k=5) -> list[str]`:
- Uses `opensearch-py` client to run the same BM25 query that `RagCommand` uses (match query on `chunk_text` field)
- Returns a list of passage text strings (the `chunk_text` field from each hit), not filenames
- Raises `RuntimeError` with a clear message if OpenSearch is unreachable

2.2 Write `generate_answer(question, searchlab_bin, dataset_index) -> str | None`:
- Calls `./searchlab rag "<question>" --top-k 5` as a subprocess using `subprocess.run`
- Captures stdout; on non-zero exit, logs a warning and returns `None`
- Strips everything from `Sources:` onward — returns only the answer block
- 60-second timeout; on `TimeoutExpired`, logs and returns `None`

2.3 Write `load_ground_truth(dataset, data_dir) -> dict[str, str] | None`:
- For FiQA: reads `data/fiqa/corpus.jsonl` and `data/fiqa/qrels/test.tsv`; for each query ID, finds the highest-relevance corpus doc and returns its `text` field as ground truth
- For nfcorpus: returns `None` (no ground truth available)
- For other datasets: returns `None` with a logged note

2.4 Write `run_rag_generation(dataset, queries, opensearch_url, index, searchlab_bin, ground_truths, slice_n) -> list[dict]`:
- Iterates over `slice_n` queries (same deterministic slice as the IR eval — use `slicer.slice_queries`)
- For each query: calls `retrieve_contexts` and `generate_answer`; if either fails, logs the query ID and skips it
- Returns list of `{query_id, question, contexts, answer, ground_truth}` dicts

2.5 Smoke check: run the function manually against FiQA with `slice_n=2`, confirm two result dicts with non-empty `answer` and `contexts` lists.

---

## Group 3 — RAGAS Scoring

Create `searchlab-eval/searchlab_eval/metrics/rag.py`.

3.1 Write `score_with_ragas(results, dataset, judge_model) -> dict`:
- Accepts the list of result dicts from Group 2
- For FiQA: builds a `ragas.Dataset` with columns `question`, `contexts`, `answer`, `ground_truth` and runs `ragas.evaluate` with all four metrics: `faithfulness`, `answer_relevancy`, `context_recall`, `context_precision`
- For nfcorpus (no ground_truth): builds dataset without `ground_truth` column and runs only `faithfulness` and `answer_relevancy`
- Uses `SEARCHLAB_LLM_JUDGE_MODEL` env var (default `gpt-4o-mini`) for the judge LLM — configure via `ragas.llms.LangchainLLMWrapper` or the RAGAS-native config, whichever is simpler with the installed version
- Per-query failures (malformed judge response): catch the exception, log the query ID, exclude from aggregate
- Returns `{aggregate: {...}, per_query: {...}, measures: [...]}`

3.2 Write `aggregate(per_query_scores, measures) -> dict`:
- Simple mean across all non-failed queries per measure
- Returns `{measure: float, ...}`

3.3 Smoke check: pass two synthetic result dicts with realistic text to `score_with_ragas`; confirm it returns a dict with at least `faithfulness` present and no exception raised.

---

## Group 4 — CLI Subcommand

Add the `ragas` subcommand to `searchlab-eval/searchlab_eval/cli.py`.

4.1 Add a new top-level `@cli.command(name="ragas")` with options:
```
--dataset / -d   required
--slice / -s     default 50
--run-id         auto-generated if omitted (same pattern as query command)
--opensearch-url default http://localhost:9200, envvar OPENSEARCH_URL
```

4.2 Command body:
1. Check `OPENAI_API_KEY` is set; if not, print clear message and `sys.exit(0)`
2. Resolve `searchlab_bin` using existing `_resolve_searchlab_bin()`; exit with error if not found
3. Load queries from `data/<dataset>/queries.jsonl`
4. Call `run_rag_generation` from `rag_runner`
5. Write `rag_results.json` to `results/<run_id>/`
6. Call `score_with_ragas` from `metrics.rag`
7. Write `rag_scores.json` to `results/<run_id>/`
8. Print the aggregate scores table to stdout (same style as the IR metrics table in `metrics.ir.format_table`)

4.3 Manual end-to-end smoke check:
```bash
cd searchlab-eval
uv run searchlab-eval ragas --dataset fiqa --slice 5
```
Expected: `rag_results.json` and `rag_scores.json` both written to `results/<run_id>/`, aggregate scores printed, no crash.

4.4 Missing API key smoke check:
```bash
OPENAI_API_KEY="" uv run searchlab-eval ragas --dataset fiqa --slice 5
```
Expected: clear message, exit 0, no stack trace.

---

## Group 5 — Java API & UI

All changes are in `src/main/java/com/searchlab/cli/WebCommand.java`.

5.1 Add `/api/eval/rag-results` route in `call()`:
```java
server.createContext("/api/eval/rag-results", this::handleRagResults);
```

5.2 Implement `handleRagResults`:
- Mirrors `handleEvalResults` exactly, except it reads `rag_scores.json` instead of `ir_scores.json`
- Same path-traversal guard (`runId.contains("..")`)
- Returns the file contents as `application/json`

5.3 Update `handleEvalRuns`:
- Add `hasRagMetrics` boolean to each run object: `Files.exists(d.resolve("rag_scores.json"))`
- Include it in the JSON output alongside existing `hasMetrics`

5.4 Update `buildEvalCommand`:
- Add a `"ragas"` case to the switch:
  ```java
  case "ragas" -> {
      List<String> cmd = new ArrayList<>(
          List.of("uv", "run", "searchlab-eval", "ragas", "--dataset", dataset));
      String slice = params.getOrDefault("slice", "");
      if (!isBlank(slice)) { cmd.add("--slice"); cmd.add(slice); }
      yield cmd;
  }
  ```

5.5 Add "RAG Eval" button to the Eval tab's `op-row`:
```html
<button class="btn eval-op-btn" onclick="runEvalOp('ragas')">RAG Eval</button>
```
Place it after the existing "Compute Metrics" button. Reuses existing SSE streaming — no new server-side code needed.

5.6 Add RAG scores panel to the Metrics tab HTML, below `<div id="metrics-content">`:
```html
<div id="rag-metrics-content" style="display:none">
  <div class="card">
    <div class="card-title" id="rag-metrics-run-label">RAG Quality Metrics</div>
    <div class="aggregate-grid" id="rag-agg-grid"></div>
    <table id="rag-pq-table">
      <thead id="rag-pq-thead"></thead>
      <tbody id="rag-pq-tbody"></tbody>
    </table>
  </div>
</div>
```

5.7 Add JavaScript constants and functions for RAG metrics:
```js
const RAG_METRICS_KEYS = [
  { key: 'faithfulness',        label: 'Faithfulness'        },
  { key: 'answer_relevancy',    label: 'Answer Relevancy'    },
  { key: 'context_recall',      label: 'Context Recall'      },
  { key: 'context_precision',   label: 'Context Precision'   },
];
```
- `loadRagMetrics()`: fetches `/api/eval/rag-results?runId=<current>` and calls `renderRagMetrics(data)`
- `renderRagMetrics(data)`: sets `rag-metrics-run-label`, renders aggregate cells in `rag-agg-grid`, renders per-query rows in `rag-pq-tbody`
- Call `loadRagMetrics()` automatically after `loadMetrics()` completes if the selected run has `hasRagMetrics: true`

5.8 Update `loadEvalRuns` JS: read `r.hasRagMetrics` from the runs response (it's now included from 5.3).

5.9 Build and verify: `mvn package -q` exits 0.

---

## Group 6 — Full Benchmark Run

6.1 Run the full 50-query eval against FiQA:
```bash
cd searchlab-eval
uv run searchlab-eval ragas --dataset fiqa --slice 50
```
Record the four aggregate scores.

6.2 Run the two-metric supplementary run against nfcorpus:
```bash
uv run searchlab-eval ragas --dataset nfcorpus --slice 50
```
Confirm only `faithfulness` and `answer_relevancy` are present in `rag_scores.json`. Confirm a clear note is logged or printed explaining why context metrics are absent.

6.3 Verify via the web UI:
```bash
./searchlab serve
```
Navigate to Metrics tab, load the FiQA run. Confirm IR scores panel and RAG scores panel both render below each other without layout breaks.

---

## Group 7 — README & Post

7.1 Update `README.md`:
- Add `ragas` to the Commands section:
  ```
  uv run searchlab-eval ragas --dataset fiqa --slice 50
  ```
  with a note that it requires `OPENAI_API_KEY` and a running `./searchlab` binary
- Add `SEARCHLAB_LLM_JUDGE_MODEL` to the environment variables table (default `gpt-4o-mini`)
- Add a note clarifying which datasets support all four metrics (FiQA) vs. two (nfcorpus)
- Add the Phase 2 benchmark row to the benchmark table

7.2 Create `posts/phase-2.md` with the following structure:
- What Phase 2 measures (and what it deliberately doesn't change)
- The four RAGAS scores from the FiQA run, with a plain-English interpretation of each
- The two nfcorpus supplementary scores
- What Phase 3 will attempt to improve

---

## Definition of Done

All groups complete when:
- [ ] `uv run searchlab-eval ragas --dataset fiqa --slice 50` runs end to end and writes both output files
- [ ] `rag_scores.json` contains all four measures for FiQA and only two for nfcorpus
- [ ] Missing `OPENAI_API_KEY` produces clear message, exit 0
- [ ] Single failing query does not abort the batch
- [ ] `mvn package -q` exits 0 with the UI changes
- [ ] Metrics tab shows RAG panel below IR panel for a run that has both files
- [ ] README `ragas` section and benchmark row are present and accurate
- [ ] `posts/phase-2.md` exists with the four FiQA scores
- [ ] See `Validation.md` for the full merge checklist
