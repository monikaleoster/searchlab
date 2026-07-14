# Phase 2 — RAG Evaluation: Requirements

## Context

Phase 1 shipped a working `rag` command: BM25 retrieval, context assembly via `ContextBuilder`, LLM generation via `LlmClient`, and answer-plus-sources output across nfcorpus and FiQA without code changes between them. The pipeline works end to end. Phase 2 is the measurement layer — it does not modify the pipeline; it holds a ruler up to it.

The retrieval ceiling is unchanged from the Phase 0 baseline:

| Dataset | nDCG@10 | Recall@10 | MAP@10 |
|---------|---------|-----------|--------|
| nfcorpus | 0.326 | 0.139 | 0.122 |
| FiQA-2018 | 0.266 | 0.342 | 0.206 |

---

## Objective

Wire RAGAS into `searchlab-eval` and produce the project's first RAG-quality numbers — faithfulness, answer relevancy, context recall, and context precision — scored against FiQA's Q&A-labeled query set. These numbers form a new benchmark row that every future phase must beat, following the same convention as the Phase 0 IR metrics.

**No pipeline changes ship in this phase.** `RagCommand`, `ContextBuilder`, and `LlmClient` are measured exactly as Phase 1 built them.

---

## Scope Decisions

### Why FiQA is the headline benchmark

Two of four RAGAS metrics require a reference answer (ground truth):

| Metric | Needs ground truth? |
|--------|---------------------|
| Faithfulness | No |
| Answer relevancy | No |
| Context recall | Yes |
| Context precision | Yes |

FiQA is the only Phase 0 dataset that ships Q&A pairs alongside IR relevance judgments. nfcorpus has qrels but no RAG-ready reference answers.

**Decision:** FiQA runs all four metrics (headline benchmark). nfcorpus runs faithfulness and answer relevancy only (supplementary), reported separately — not blended into FiQA's numbers.

### Slice size

Default: 50 queries, matching Phase 0's first benchmark run. Controlled by the existing `--slice` flag. Running the full 648-query FiQA corpus is costly and not fully reproducible due to LLM-as-judge variance.

### Batch execution

The Phase 1 RAG pipeline must be callable per query **in-process** — no JVM subprocess spawned per query. This requires confirming that `RagCommand` logic can be invoked programmatically from the Python harness.

### Judge model

A dedicated `SEARCHLAB_LLM_JUDGE_MODEL` env var (default: `gpt-4o-mini`) controls the RAGAS judge, separate from `SEARCHLAB_LLM_MODEL` (which controls answer generation). This keeps judge and generator decoupled and swappable.

---

## Functional Requirements

| # | Requirement |
|---|-------------|
| F1 | `searchlab-eval ragas --dataset fiqa --slice 50` runs end to end and produces `rag_results.json` and `rag_scores.json`. |
| F2 | `rag_results.json` schema: `{ query_id, question, contexts: [...], answer, ground_truth }` per query; ground_truth is null for nfcorpus. |
| F3 | `rag_scores.json` schema mirrors `ir_scores.json`: `{ aggregate: {...}, per_query: [...] }`. |
| F4 | FiQA produces all four RAGAS metrics. nfcorpus produces faithfulness and answer relevancy only, with a logged note that ground-truth metrics are omitted. |
| F5 | Missing `OPENAI_API_KEY` produces a clear message, skips generation, and exits 0 — no stack trace or hang. |
| F6 | A single query's RAGAS scoring failure is logged and excluded from the aggregate; the batch does not abort. |
| F7 | Metrics tab gains a RAG score panel alongside (not replacing) the existing IR metrics panel. |
| F8 | README documents the new command, `SEARCHLAB_LLM_JUDGE_MODEL`, and dataset metric coverage. |

---

## Out of Scope

| Item | Phase |
|------|-------|
| Changes to retrieval, chunking, or prompts in response to scores | Phase 3 |
| Semantic or hybrid retrieval | Phase 3 |
| Re-ranking, HyDE, query expansion | Phase 4 |
| Full four-metric nfcorpus evaluation | Not planned (no reference answers) |
| CI-gated RAG score regression testing | Unscheduled |
| Local/open-source judge model | Open question |
