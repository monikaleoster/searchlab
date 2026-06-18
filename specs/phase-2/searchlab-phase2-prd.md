# SearchLab — Phase 2 PRD
## RAG Evaluation

> Phase 1 built a RAG loop that runs. Phase 2 is the ruler held up to it — the first numbers on whether the answers it produces are any good.

---

| Field | Value |
|-------|-------|
| Document | SearchLab Phase 2 PRD |
| Phase | Phase 2: RAG Evaluation |
| Status | Draft |
| Depends On | Phase 1 (RAG with BM25 + web UI) — COMPLETE |
| Feeds Into | Phase 3: Structured chunking vs. semantic retriever |
| Eval Framework | RAGAS — faithfulness, answer relevancy, context recall, context precision |
| Stack | Java 21, OpenSearch 2.19.0, Python 3.12, ragas, OpenAI API, uv |

---

## 1. Context

Phase 1 shipped a working `rag` command: BM25 retrieval, context assembly, LLM generation, answer plus sources, against both nfcorpus and FiQA without code changes between them. It works end to end. Working and good are different claims, and Phase 1 said so explicitly — the only failure mode its own pipeline can detect is empty retrieval. Everything past that point is the model doing its best with whatever it was handed, with no measurement of whether that was any good.

The retrieval ceiling underneath all of this is still the Phase 0 baseline, unchanged:

| Dataset | nDCG@10 | Recall@10 | MAP@10 |
|---------|---------|-----------|--------|
| nfcorpus | 0.326 | 0.139 | 0.122 |
| FiQA-2018 | 0.266 | 0.342 | 0.206 |

Phase 2 doesn't touch retrieval. It measures what the Phase 1 pipeline produces from that retrieval, using the four RAGAS metrics already stubbed behind the `--rag` flag in `searchlab-eval` since Phase 0.

## 2. Objective

Wire RAGAS into `searchlab-eval` and produce the project's first RAG-quality numbers: faithfulness, answer relevancy, context recall, and context precision, scored against FiQA's Q&A-labeled query set. The result is a new row in the benchmark table, sitting beside the Phase 0 IR metrics, that every future phase has to beat — the same convention the project already applies to retrieval.

No pipeline changes ship in this phase. `RagCommand`, `ContextBuilder`, and `LlmClient` are measured exactly as Phase 1 built them. This phase is a ruler, not a wrench.

## 3. Scope Decision — why FiQA carries this phase

Two of the four RAGAS metrics need a reference answer to compute:

| Metric | Needs ground truth? | What it answers |
|--------|---------------------|------------------|
| Faithfulness | No | Does the answer stay within what the retrieved passages actually say? |
| Answer relevancy | No | Does the answer address the question asked, rather than a fluent non-answer? |
| Context recall | Yes | Of what the reference answer needed, how much did retrieval surface? |
| Context precision | Yes | Of what got retrieved, how much was actually relevant? |

FiQA has Q&A pairs alongside its IR relevance judgments — the only Phase 0 dataset that does. nfcorpus has qrels but no RAG-ready reference answers. That means nfcorpus can only support the two ground-truth-free metrics. Rather than force a partial four-metric run or skip nfcorpus entirely, Phase 2 treats FiQA as the headline benchmark (all four metrics) and nfcorpus as a supplementary two-metric read, reported separately rather than blended into one number.

## 4. Evaluation Design

**Pipeline shape**, building on the existing `run` command's structure:

1. **Retrieval** (existing) — BM25 hits per query, already produced by the current eval harness.
2. **Generation** (new) — for each query, run the Phase 1 RAG pipeline (`ContextBuilder` → `LlmClient`, called in-process or via the existing `RagCommand` logic, not a CLI subprocess per query) and capture the generated answer alongside the retrieved contexts. Output: `rag_results.json` — `{query_id, question, contexts: [...], answer, ground_truth}` per query, ground_truth populated only where the dataset provides one.
3. **Scoring** (new) — `uv run searchlab-eval ragas --dataset fiqa --slice 50` reads `rag_results.json` and computes the four RAGAS scores, writing `rag_scores.json` in the same aggregate-plus-per-query shape as the existing `ir_scores.json`, so the web UI's Metrics tab can render both with one pattern.
4. **Display** (new) — Metrics tab gains a second score panel beside the existing IR metrics table. Additive only; nothing about the current IR display changes.

**Judge model.** RAGAS scores are themselves LLM-judged. A new `SEARCHLAB_LLM_JUDGE_MODEL` env var (separate from `SEARCHLAB_LLM_MODEL`, which generates the RAG answer) defaults to `gpt-4o-mini` for cost control and is swappable, same convention as Phase 1's model flag.

**Slice size.** Running judge plus generation calls across all 648 FiQA queries is costly and, because LLM-as-judge has run-to-run variance even at low temperature, not fully reproducible at any size. Phase 2 evaluates a slice rather than the full set, defaulting to 50 queries — the same number Phase 0 used for its own first benchmark run — via the existing `--slice` flag.

## 5. Technical Requirements

- New Python dependency: `ragas`, already anticipated and stubbed behind `searchlab-eval`'s `--rag` flag since Phase 0.
- New `searchlab-eval ragas` subcommand, reusing the existing `--dataset` and `--slice` arguments rather than introducing a parallel flag set.
- The Phase 1 RAG pipeline must be callable per query from the Python harness without spawning a JVM per call — see Open Questions for the batch-execution decision this depends on.
- `rag_results.json` and `rag_scores.json` schemas mirror `raw_results.json` / `ir_scores.json`'s existing shape (aggregate + `per_query`) so the Metrics tab can reuse its existing render path.
- Error handling: missing `OPENAI_API_KEY` produces the same clear-message-and-skip behavior Phase 1 established, not a new error path. A single query's RAGAS scoring failure (a malformed judge response, a timeout) is logged and that query is excluded from the aggregate, rather than aborting the whole batch — one bad response shouldn't void a 50-query run.
- No Java code changes required beyond exposing a programmatic (non-subprocess) entry point to the RAG pipeline, if that turns out to be necessary per the batch-execution open question.

## 6. Out of Scope

| Deferred item | Phase |
|----------------|-------|
| Any change to retrieval, chunking, or prompt made *in response to* low scores | 3 (retrieval/chunking) — prompt tuning is unscheduled |
| Semantic or hybrid retrieval | 3 |
| Re-ranking, HyDE, query expansion | 4 |
| Full four-metric nfcorpus evaluation | — (no reference answers exist; see Scope Decision) |
| CI-gated regression testing on RAG scores | Unscheduled — DeepEval candidate if this becomes a recurring need |
| Local/open-source judge model | Open question below |

## 7. Acceptance Criteria

| Criterion | Pass | Fail |
|-----------|------|------|
| `searchlab-eval ragas --dataset fiqa --slice 50` runs end to end | All four scores present in `rag_scores.json` | Crash, or partial output with no explanation |
| nfcorpus produces its two ground-truth-free metrics | Faithfulness + answer relevancy present, others omitted with a clear note | Missing entirely, or a four-metric run silently attempted |
| Missing `OPENAI_API_KEY` handled | Clear message, skip, exit 0 | Stack trace or hang |
| A single failed query doesn't void the run | Run completes; failed query logged and excluded | Whole batch aborts |
| Metrics tab displays RAG scores beside IR scores | Both panels visible, no layout break | One hides or overwrites the other |
| README documents the new command and env var | Reproducible on a fresh clone | Missing or broken |

## 8. What Phase 2 Does Not Measure

Phase 2 tells us whether the Phase 1 pipeline, exactly as built, produces faithful and relevant answers from what it retrieves. It does not tell us whether a *different* pipeline would score higher. Specifically out of view:

- Whether structured chunking or a semantic retriever would lift context recall — that's Phase 3's question, and the reason this phase doesn't touch retrieval at all.
- Whether a different prompt template would lift faithfulness without touching retrieval — open, unscheduled.
- Whether the scores hold at full-corpus scale rather than a 50-query slice.
- Whether judge-model choice materially shifts the numbers — a methodological question every later phase inherits, not just this one.

## 9. Definition of Done

1. `searchlab-eval ragas` ships and runs against FiQA, producing all four RAGAS scores in `rag_scores.json`.
2. nfcorpus produces its two-metric partial read.
3. Metrics tab in the web UI displays RAG scores alongside the existing IR scores.
4. README documents the new command, the new env var, and which dataset supports which metrics.
5. Benchmark table gets its first RAG-quality row — Phase 1's "no quality measurement ships" caveat is retired.
6. Phase 2 post published with the four numbers and a plain-English read of what they mean.

## 10. Open Questions

- **Batch execution.** Calling the Phase 1 RAG pipeline once per query either means spawning the Java CLI as a subprocess 50 times (slow, simple) or exposing a programmatic batch entry point the Python harness can call directly (faster, requires new Java surface area). Needs deciding before implementation starts.
- **Judge model choice.** `gpt-4o-mini` (cheap, consistent with the generation model) versus `gpt-4o` (likely a more reliable judge, costs more) versus a local model via Ollama (no marginal cost, judge quality unproven). Revisit DeepEval's local-judge support if cost becomes a recurring concern.
- **Run-to-run variance.** LLM-as-judge scoring isn't fully deterministic even when the generation step is pinned at temperature 0, since RAGAS's internal judge prompts aren't necessarily temperature-controlled. Decide whether Phase 2 reports a single run or an average across several.
- **Slice size vs. confidence.** Fifty queries is a convenience number carried over from Phase 0, not a power calculation. Worth revisiting once the first scores are in hand and their spread is visible.

---

*SearchLab is built in public. All PRDs, benchmark results, and code are in the repo. This document is the spec for Phase 2 only.*
