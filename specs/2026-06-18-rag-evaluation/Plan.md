# Phase 2 — RAG Evaluation: Implementation Plan

> **Architecture decision:** `searchlab-eval ragas` remains the CLI entry point and owns the
> full evaluation loop. It does **not** run LLM logic directly — it calls the service's existing
> `POST /rag` endpoint once per query for answer generation, then runs RAGAS scoring locally.
> The service is unchanged except for the `SEARCHLAB_LLM_JUDGE_MODEL` config addition.

---

## Group 1 — Dependency & Config Setup

**Where:** `searchlab-eval/pyproject.toml` · `service/searchlab/config.py`

1.1 Move `ragas` from the `[rag]` optional extra into the main `dependencies` list in
    `searchlab-eval/pyproject.toml` so it is always installed.

1.2 Add `SEARCHLAB_LLM_JUDGE_MODEL` to `service/searchlab/config.py` (default: `gpt-4o-mini`).
    This is separate from `SEARCHLAB_LLM_MODEL`, which controls what the service uses for
    answer generation. The judge model is read by `searchlab-eval` at scoring time.

1.3 Run `uv sync` inside `searchlab-eval/` and confirm `import ragas` resolves without error.

---

## Group 2 — `searchlab-eval ragas` CLI command

**Where:** `searchlab-eval/searchlab_eval/cli.py` + new `searchlab_eval/rag_eval.py`

2.1 Add a top-level `ragas` command to the Click CLI (not a subcommand of `metrics`):
    ```
    searchlab-eval ragas --dataset <name> --slice <n> [--searchlab-url <url>] [--run-id <id>]
    ```
    Reuse the existing `--dataset`, `--slice`, and `--searchlab-url` options by referencing
    the shared option objects already defined in `cli.py`.

2.2 If `--run-id` is omitted, generate one as `{dataset}-ragas-{timestamp}` and create
    `results/{run_id}/` automatically.

---

## Group 3 — Generation Step (calls `POST /rag`)

**Where:** `searchlab-eval/searchlab_eval/rag_eval.py`

3.1 Load the query slice from `data/{dataset}/queries.jsonl` using the existing
    `load_queries()` from `querier.py`.

3.2 For each query, POST to `{SEARCHLAB_URL}/rag` with form fields
    `question`, `topK=10`, `dataset`. Capture:
    - `answer` — the LLM-generated response
    - `sources[].filename` and the retrieved passage text (for context)

    ```
    POST /rag
    Content-Type: application/x-www-form-urlencoded
    question=...&topK=10&dataset=fiqa
    ```

3.3 Load ground truth answers for FiQA from `data/fiqa/qrels/` cross-referenced with
    the corpus to populate `ground_truth`; set to `null` for nfcorpus.

3.4 Collect per-query records into `rag_results.json`:
    ```json
    {
      "run_id": "...",
      "dataset": "...",
      "generated_at": "...",
      "per_query": [
        {
          "query_id": "...",
          "question": "...",
          "contexts": ["..."],
          "answer": "...",
          "ground_truth": "..." 
        }
      ]
    }
    ```

3.5 Error handling for the generation loop:
    - If the service returns `{ "error": "OPENAI_API_KEY not set" }`, print a clear
      message and exit 0 — no stack trace.
    - If a single query's `/rag` call fails (timeout, HTTP error), log it and skip that
      query; the batch does not abort.

---

## Group 4 — Scoring Step (RAGAS, local in `searchlab-eval`)

**Where:** `searchlab-eval/searchlab_eval/rag_eval.py`

4.1 After generation completes, load `rag_results.json` from the run directory.

4.2 Read `SEARCHLAB_LLM_JUDGE_MODEL` from the environment (default `gpt-4o-mini`) and
    log it at the start of scoring so runs are reproducible.

4.3 Run RAGAS metrics locally:
    - **FiQA**: all four — `faithfulness`, `answer_relevancy`, `context_recall`,
      `context_precision`.
    - **nfcorpus**: `faithfulness` and `answer_relevancy` only. Log a clear note that
      the ground-truth metrics are omitted; do not attempt to compute them.

4.4 Write `rag_scores.json` mirroring the shape of `ir_scores.json`:
    ```json
    {
      "run_id": "...",
      "dataset": "...",
      "computed_at": "...",
      "measures": ["faithfulness", "answer_relevancy", ...],
      "aggregate": { "faithfulness": 0.0, "answer_relevancy": 0.0, ... },
      "per_query": { "<query_id>": { "faithfulness": 0.0, ... }, ... }
    }
    ```

4.5 Per-query failure handling: a malformed or timed-out RAGAS judge response is caught,
    logged with the query ID, and excluded from the aggregate — the batch does not abort.

---

## Group 5 — Web UI: Metrics Tab

**Where:** `service/searchlab/web/html.py` (read-only verification)

5.1 The Eval tab's **RAG Eval** button already calls `runEvalOp('ragas')`, which hits
    `GET /api/eval/stream?op=ragas&dataset=...&slice=...`. The service's
    `_build_eval_command` already maps this to `uv run searchlab-eval ragas`.
    No UI change required once the CLI command exists.

5.2 Confirm `GET /api/eval/runs` returns `hasRagMetrics: true` for runs that have
    `rag_scores.json` — the backend already does this check.

5.3 Confirm `GET /api/eval/rag-results?runId=...` returns the `rag_scores.json` payload —
    the backend route already exists.

5.4 Confirm the Metrics tab's RAG panel renders on load (the `loadRagMetrics()` /
    `renderRagMetrics()` JS functions are already wired up). No JS changes required.

5.5 Smoke-test: load a run with both `ir_scores.json` and `rag_scores.json` — verify both
    panels are visible with no layout break.

---

## Group 6 — README & Documentation

6.1 Document the `searchlab-eval ragas` command with a full usage example showing
    `SEARCHLAB_URL`, `SEARCHLAB_LLM_MODEL`, and `SEARCHLAB_LLM_JUDGE_MODEL`.

6.2 Document which datasets support which metrics:
    - FiQA: faithfulness, answer relevancy, context recall, context precision
    - nfcorpus: faithfulness, answer relevancy only

6.3 Add the first RAG-quality row to the benchmark table once a real run produces scores.

6.4 Confirm the instructions are reproducible on a fresh clone — no undocumented env
    vars, no assumption that the service is already running.
