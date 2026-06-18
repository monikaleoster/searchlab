# Phase 2 — RAG Evaluation: Validation

## Acceptance Criteria

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| AC1 | `searchlab-eval ragas --dataset fiqa --slice 50` runs end to end | All four scores present in `rag_scores.json` | Crash, partial output with no explanation |
| AC2 | nfcorpus produces its two ground-truth-free metrics | Faithfulness + answer relevancy present; context recall and context precision explicitly omitted with a logged note | Missing entirely, or a four-metric run silently attempted |
| AC3 | Missing `OPENAI_API_KEY` handled gracefully | Clear message, skip, exit 0 | Stack trace or hang |
| AC4 | Single failed query doesn't abort the run | Run completes; failed query logged and excluded from aggregate | Whole batch aborts |
| AC5 | Metrics tab displays RAG scores beside IR scores | Both panels visible, no layout break | One panel hides or overwrites the other |
| AC6 | `rag_scores.json` schema matches `ir_scores.json` shape | `aggregate` + `per_query` present and renderable by existing Metrics tab pattern | Schema mismatch causing render failure |
| AC7 | README documents new command and env var | Reproducible on a fresh clone | Missing or broken instructions |
| AC8 | Benchmark table updated with first RAG-quality row | Row present with four FiQA scores and two nfcorpus scores | No update made |

---

## Manual Verification

### 1. End-to-end FiQA run

```bash
export OPENAI_API_KEY=<key>
export SEARCHLAB_LLM_MODEL=gpt-4o-mini
export SEARCHLAB_LLM_JUDGE_MODEL=gpt-4o-mini
uv run searchlab-eval ragas --dataset fiqa --slice 50
```

- Confirm `rag_results.json` is written with 50 entries, each containing `query_id`, `question`, `contexts`, `answer`, and `ground_truth`.
- Confirm `rag_scores.json` is written with an `aggregate` block containing all four metrics: `faithfulness`, `answer_relevancy`, `context_recall`, `context_precision`.
- Confirm `per_query` in `rag_scores.json` has 50 entries (minus any logged failures).

### 2. nfcorpus partial run

```bash
uv run searchlab-eval ragas --dataset nfcorpus --slice 50
```

- Confirm only `faithfulness` and `answer_relevancy` appear in `rag_scores.json` aggregate.
- Confirm a log message explicitly states that context recall and context precision are omitted due to missing ground truth.
- Confirm no crash or silent partial output.

### 3. Missing API key

```bash
unset OPENAI_API_KEY
uv run searchlab-eval ragas --dataset fiqa --slice 50
```

- Confirm exit code is 0.
- Confirm the output includes a human-readable message (e.g., "OPENAI_API_KEY not set — skipping RAG generation").
- Confirm no stack trace appears.

### 4. Single query failure resilience

- Temporarily inject a malformed or empty response for one query in a test/debug mode, or observe natural failure during a run.
- Confirm the run completes with the remaining queries scored.
- Confirm the failed query appears in logs with a clear reason.
- Confirm aggregate scores are computed from the non-failed subset.

### 5. Web UI — Metrics tab

- Start the web app and navigate to the Metrics tab.
- Load a dataset that has both `ir_scores.json` and `rag_scores.json` present.
- Confirm both panels render without overlap or layout breakage.
- Load a dataset with only `ir_scores.json` — confirm RAG panel is absent, IR panel is unaffected.
- Load the nfcorpus dataset — confirm only two metrics appear in the RAG panel, with a label indicating partial coverage.

### 6. README reproducibility

- On a fresh terminal (or with env cleared), follow the README instructions exactly.
- Confirm `searchlab-eval ragas` runs without undocumented setup.
- Confirm `SEARCHLAB_LLM_JUDGE_MODEL` is listed and its default (`gpt-4o-mini`) is noted.

---

## Merge Checklist

- [ ] AC1–AC8 all pass.
- [ ] Manual verification steps 1–6 completed and noted (scores, pass/fail per step).
- [ ] Benchmark table in README updated with actual FiQA four-metric scores and nfcorpus two-metric scores from a real run.
- [ ] No changes to `RagCommand`, `ContextBuilder`, or `LlmClient` — if any Java changes were necessary, they are additive (new programmatic entry point only) and reviewed separately.
- [ ] `rag_scores.json` shape confirmed compatible with existing Metrics tab render path (no new frontend patterns required).
- [ ] Phase 2 post drafted with the four FiQA numbers and a plain-English read.
