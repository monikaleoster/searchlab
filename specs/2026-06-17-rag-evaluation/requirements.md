# Requirements — Phase 2: RAG Evaluation

**Phase:** 2
**Feature:** Wire RAGAS into searchlab-eval; produce the project's first RAG-quality numbers
**Status:** In progress
**Spec source:** `specs/phase-2/searchlab-phase2-prd.md`
**Depends on:** Phase 1 complete (RagCommand, ContextBuilder, LlmClient, web UI — all on `Phase-1-RAG`)
**Feeds into:** Phase 3 — structured chunking vs. semantic retriever

---

## Context

Phase 1 shipped a working `rag` command. Working and good are different claims. The retrieval ceiling is still the Phase 0 BM25 baseline (nfcorpus nDCG@10 0.326, FiQA nDCG@10 0.266). Phase 2 measures what the pipeline produces from that retrieval — the first numbers on whether the answers are any good.

Phase 2 is a ruler, not a wrench. No pipeline changes ship. `RagCommand`, `ContextBuilder`, and `LlmClient` are measured exactly as Phase 1 built them.

---

## Objective

Produce four RAGAS scores against FiQA (all four metrics) and two scores against nfcorpus (faithfulness + answer relevancy only). Add a RAG scores panel to the Metrics tab. The result is a new row in the benchmark table that every future phase has to beat.

---

## Scope Decisions

### Decided

| Decision | Choice | Why |
|----------|--------|-----|
| Batch execution | Subprocess per query (50× `./searchlab rag`) | No Java changes; JVM startup cost is acceptable at 50 queries |
| Judge model | `gpt-4o-mini` | Cost-effective; same model used for generation; sufficient for a first-pass benchmark |
| Run-to-run variance | Single run reported | Consistent with how Phase 0 IR baseline was reported; variance acknowledged but not compensated for |
| Metrics tab layout | Second panel below IR metrics | Additive; no layout changes to current IR display |
| Slice size | 50 queries | Same as Phase 0 first-run convention; revisit once first scores are in hand |
| Dataset | FiQA headline (4 metrics), nfcorpus supplementary (2 metrics) | FiQA has qrels-backed ground truth; nfcorpus does not |

### Ground Truth Construction

FiQA's ground truth for RAGAS is constructed from qrels: for each query, the text of the highest-relevance corpus document (from `qrels/test.tsv`) is used as the reference answer. nfcorpus has no equivalent; context_recall and context_precision are skipped for that dataset.

### Context Retrieval for RAGAS

RAGAS needs `contexts` (the actual passage text, not just source filenames). Since the subprocess approach means `./searchlab rag` only prints the answer and source filenames, the Python harness uses its existing OpenSearch client to retrieve the same top-5 BM25 passages that the Java pipeline would retrieve. Retrieval parameters (top-k=5, BM25, same index) must match what `RagCommand` uses.

---

## In Scope

- `searchlab_eval/rag_runner.py` — per-query generation + context capture, writes `rag_results.json`
- `searchlab_eval/metrics/rag.py` — RAGAS scoring, writes `rag_scores.json`
- New `ragas` CLI subcommand: `searchlab-eval ragas --dataset <name> --slice 50 --run-id <id>`
- `SEARCHLAB_LLM_JUDGE_MODEL` env var (defaults to `gpt-4o-mini`)
- `/api/eval/rag-results` endpoint in `WebCommand.java`
- RAG scores panel in the Metrics tab (below IR scores; additive only)
- `buildEvalCommand` updated to handle `op=ragas`
- README: new command, new env var, which dataset supports which metrics
- `posts/phase-2.md` with the four numbers and a plain-English read

## Out of Scope

| Deferred item | Phase |
|---------------|-------|
| Any pipeline change made in response to low scores | 3+ |
| Semantic or hybrid retrieval | 3 |
| Re-ranking, HyDE, query expansion | 4 |
| Full four-metric nfcorpus run (no reference answers exist) | — |
| CI-gated regression on RAG scores | Unscheduled |
| Local/open-source judge model | Unscheduled |
| Averaging across multiple runs | Unscheduled |

---

## File Schemas

### `rag_results.json` (written by `rag_runner.py`)

Stored at `searchlab-eval/results/<run_id>/rag_results.json`.

```json
{
  "run_id": "fiqa-20260617T120000Z",
  "dataset": "fiqa",
  "slice_n": 50,
  "created_at": "2026-06-17T12:00:00Z",
  "results": [
    {
      "query_id": "q1",
      "question": "what is dollar cost averaging",
      "contexts": ["passage text 1", "passage text 2"],
      "answer": "Dollar cost averaging is...",
      "ground_truth": "reference answer text"
    }
  ]
}
```

`ground_truth` is `null` for nfcorpus entries.

### `rag_scores.json` (written by `metrics/rag.py`)

Stored at `searchlab-eval/results/<run_id>/rag_scores.json`. Mirrors `ir_scores.json` shape.

```json
{
  "run_id": "fiqa-20260617T120000Z",
  "dataset": "fiqa",
  "computed_at": "2026-06-17T12:01:00Z",
  "judge_model": "gpt-4o-mini",
  "measures": ["faithfulness", "answer_relevancy", "context_recall", "context_precision"],
  "aggregate": {
    "faithfulness": 0.75,
    "answer_relevancy": 0.82,
    "context_recall": 0.68,
    "context_precision": 0.71
  },
  "per_query": {
    "q1": {
      "faithfulness": 0.9,
      "answer_relevancy": 0.85,
      "context_recall": 0.7,
      "context_precision": 0.8
    }
  }
}
```

For nfcorpus: `measures` is `["faithfulness", "answer_relevancy"]`; context_recall and context_precision are absent from aggregate and per_query.

---

## Error Handling Contract

| Scenario | Behaviour |
|----------|-----------|
| Missing `OPENAI_API_KEY` | Clear message to stderr, exit 0 (consistent with Phase 1 convention) |
| Missing `SEARCHLAB_LLM_JUDGE_MODEL` | Default to `gpt-4o-mini`; no error |
| Single query RAGAS scoring failure (malformed judge response, timeout) | Log query ID and error, exclude from aggregate, continue batch |
| `./searchlab rag` subprocess returns non-zero | Log warning, mark query as failed, continue |
| `rag_results.json` not found when scoring | Clear error message, exit non-zero |
| OpenSearch unavailable during context retrieval | Surface connection error with human-readable message, exit non-zero |

---

## Technical Constraints (from CONSTITUTION.md)

- Python 3.12, uv, Click — no new CLI frameworks
- `ragas` already listed as optional dep in `pyproject.toml`; install as required for Phase 2
- No secrets in repo; `SEARCHLAB_LLM_JUDGE_MODEL` and `OPENAI_API_KEY` in `.env.example` only
- No Java changes required (subprocess approach chosen)
- No change to existing IR metrics display in Metrics tab
