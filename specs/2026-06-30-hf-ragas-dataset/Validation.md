# HuggingFace RAGAS Dataset: Validation

> Per the Constitution (Section VII), a phase is not complete because the code works.
> Every criterion below must pass before this work is merged.

---

## Acceptance Criteria

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| AC1 | `download --dataset vibrantlabsai/fiqa` fetches and writes `records.jsonl` | File exists at `data/vibrantlabsai-fiqa/records.jsonl`; record count printed | Crash, missing file, or zero records |
| AC2 | `ragas --dataset vibrantlabsai/fiqa --slice 50` reads from disk (no HF network call at eval time) | Run completes with HF network disconnected after download | Fails or hangs without HF access |
| AC3 | Dataset type detected automatically by `/` in name; no new flags needed | Both `fiqa` and `vibrantlabsai/fiqa` route correctly without extra options | Routing fails or requires an explicit flag |
| AC4 | BEIR `ragas` path unchanged | `ragas --dataset fiqa` produces identical output to pre-change baseline | Score change, crash, or schema difference |
| AC5 | All four RAGAS metrics present for HF datasets | `faithfulness`, `answer_relevancy`, `context_recall`, `context_precision` all in `rag_scores.json` aggregate | Any metric missing |
| AC6 | `ground_truth` in `rag_results.json` is from HF records, never null | All sliced records have a non-empty `ground_truth` string | Null values or qrel-derived passage text |
| AC7 | `rag_results.json` and `rag_scores.json` schemas identical to Phase 2 | Existing Metrics tab renders HF run without code changes | Schema mismatch causing render failure |
| AC8 | `ragas` before `download` produces a clear error | Message names missing file and the download command to run | Silent empty result or Python traceback |
| AC9 | Missing `OPENAI_API_KEY` handled gracefully | Clear human-readable message; exit 0; no stack trace | Stack trace or hang |
| AC10 | Single query failure does not abort the run | Batch completes; failed query logged with ID and reason | Whole batch aborts |
| AC11 | README documents the three-step HF flow and the prerequisite BEIR ingest | Reproducible on a fresh clone following only README instructions | Missing or incomplete docs |
| AC12 | Benchmark table updated with `HF FiQA (system)` row | Row present with four real scores from an actual run | No update or placeholder values |

---

## Manual Verification

### 1. Download

```bash
cd searchlab-eval
uv run searchlab-eval download --dataset vibrantlabsai/fiqa
```

Check:
- `data/vibrantlabsai-fiqa/records.jsonl` exists.
- Record count is printed to stdout.
- Each line is valid JSON with `question` and `ground_truth` fields.
- Re-running download overwrites cleanly without error.

### 2. Ragas — end to end (system mode)

Prerequisites: BEIR FiQA corpus ingested (`searchlab-eval ingest --dataset fiqa`), service
running at `http://localhost:8080`, `OPENAI_API_KEY` set.

```bash
export OPENAI_API_KEY=<key>
export SEARCHLAB_LLM_MODEL=gpt-4o-mini
export SEARCHLAB_LLM_JUDGE_MODEL=gpt-4o-mini

uv run searchlab-eval ragas --dataset vibrantlabsai/fiqa --slice 50
```

Check:
- `results/vibrantlabsai-fiqa-ragas-*/rag_results.json` written with 50 entries.
- Every entry has a non-empty `ground_truth` string.
- `rag_scores.json` has all four metrics in `aggregate`.
- `per_query` count matches successful queries.
- Top-level `"source": "hf"` field present in `rag_results.json`.

### 3. No HF network call at eval time

After download completes, disconnect from the internet (or block `huggingface.co`) and run:

```bash
uv run searchlab-eval ragas --dataset vibrantlabsai/fiqa --slice 50
```

Check: command completes successfully — no HF network call is made at eval time.

### 4. BEIR path regression

```bash
uv run searchlab-eval ragas --dataset fiqa --slice 50
```

Check: scores match the Phase 2 baseline (within expected LLM-as-judge variance). No schema
change, no crash, no change in metric selection behaviour.

### 5. Missing download error

```bash
rm -rf data/vibrantlabsai-fiqa/
uv run searchlab-eval ragas --dataset vibrantlabsai/fiqa --slice 50
```

Check:
- Clear error message naming the missing file.
- Message includes the download command to run.
- No Python traceback.

### 6. Missing API key

```bash
unset OPENAI_API_KEY
uv run searchlab-eval ragas --dataset vibrantlabsai/fiqa --slice 50
```

Check: exit code 0, clear message, no stack trace.

### 7. Single query failure resilience

Observe or simulate a single `/rag` call failure (e.g., very short timeout):
- Run completes with remaining queries scored.
- Failed query logged with ID and reason.
- Aggregate computed from non-failed subset only.

### 8. Metrics tab compatibility

- Run `ragas --dataset fiqa` (BEIR) and `ragas --dataset vibrantlabsai/fiqa` (HF).
- Load both runs in the Metrics tab.
- Confirm both RAG score panels render correctly; no JS console errors.

### 9. README reproducibility

On a fresh terminal with env cleared, follow the three-step HF flow in the README exactly.
Confirm no undocumented setup, no assumption about pre-ingested data without a documented
prerequisite step.

---

## Comparison Baseline

Populate before merge (Constitution § II — no change ships without a number).

| Run | Faithfulness | Answer Relevancy | Context Recall | Context Precision |
|-----|-------------|-----------------|----------------|-------------------|
| FiQA BEIR (qrel-derived GT) | _from Phase 2_ | _from Phase 2_ | _from Phase 2_ | _from Phase 2_ |
| `vibrantlabsai/fiqa` (HF GT) | | | | |

---

## Merge Checklist

> A phase is done or it is in progress. There is no "almost done." — Constitution § X

- [ ] AC1–AC12 all pass.
- [ ] Manual verification steps 1–9 completed; pass/fail noted for each.
- [ ] Comparison baseline table populated with real scores from actual runs.
- [ ] Benchmark table in `docs/wiki.md` updated with `HF FiQA (system)` row.
- [ ] BEIR `ragas` path produces identical output to pre-change baseline (AC4 confirmed).
- [ ] No changes to `RagCommand`, `ContextBuilder`, `LlmClient`, or any BEIR evaluation path.
- [ ] `datasets` declared explicitly in `pyproject.toml`.
- [ ] `hf_downloader.py` unit test covers: split auto-selection, missing file error, `slice_hf` boundary.
- [ ] `prompts/history.md` updated with the prompt that initiated this session (Constitution § VII step 0).