# Validation — Phase 2: RAG Evaluation

This document defines what "done" means for Phase 2 and how to verify it. Work through each section before merging to main.

Prerequisites for all manual steps: `docker compose up` is running, FiQA and nfcorpus are indexed (`searchlab-eval ingest`), and `OPENAI_API_KEY` is set.

---

## 1. Automated Checks

Run these first. Manual steps are irrelevant if these fail.

```bash
# Python eval harness
cd searchlab-eval
uv run pytest                          # all existing tests pass

# Java build
cd ..
mvn package -q                         # fat JAR builds clean
mvn test                               # unit tests pass
```

Pass criteria:
- [ ] `uv run pytest` exits 0, no regressions in existing IR eval tests
- [ ] `mvn package` exits 0, `target/searchlab.jar` exists
- [ ] `mvn test` exits 0

---

## 2. Acceptance Criteria (from PRD §7)

| # | Criterion | How to verify | Pass | Fail |
|---|-----------|---------------|------|------|
| AC-1 | `ragas --dataset fiqa --slice 50` produces all four scores | Check `rag_scores.json` for `faithfulness`, `answer_relevancy`, `context_recall`, `context_precision` in `aggregate` | All four present, values between 0–1 | Missing metric, crash, or partial output with no explanation |
| AC-2 | nfcorpus produces only two metrics | Check `rag_scores.json` for nfcorpus run — only `faithfulness` and `answer_relevancy` in `measures` | Two metrics, clear note logged about omitted ones | Four-metric run silently attempted, or metrics absent entirely |
| AC-3 | Missing `OPENAI_API_KEY` handled | `OPENAI_API_KEY="" uv run searchlab-eval ragas --dataset fiqa --slice 5` | Clear message to stderr, exit 0 | Stack trace or hang |
| AC-4 | Single failed query doesn't abort the batch | Inject a bad query or simulate a judge timeout; check run completes | Run completes, failed query logged, excluded from aggregate | Whole batch aborts |
| AC-5 | Metrics tab shows RAG panel below IR panel | Load a run that has `rag_scores.json` in the web UI Metrics tab | Both panels visible, no overlap or hidden content | One panel hides or overwrites the other |
| AC-6 | README documents the new command and env var | Follow README from a fresh-clone perspective | Command and env var reproducible | Missing or broken |

---

## 3. Manual Verification Steps

### 3.1 FiQA full 50-query run

```bash
cd searchlab-eval
uv run searchlab-eval ragas --dataset fiqa --slice 50
```

Expected:
- Progress output per query (or a progress bar) as the 50 subprocesses run
- Aggregate scores table printed at the end (four rows: faithfulness, answer_relevancy, context_recall, context_precision)
- `results/<run_id>/rag_results.json` exists with 50 entries (minus any failed queries)
- `results/<run_id>/rag_scores.json` exists with four measures in `aggregate`
- All score values are between 0 and 1

### 3.2 nfcorpus supplementary run

```bash
uv run searchlab-eval ragas --dataset nfcorpus --slice 50
```

Expected:
- Aggregate prints only faithfulness and answer_relevancy
- `rag_scores.json` has `"measures": ["faithfulness", "answer_relevancy"]`
- `context_recall` and `context_precision` are absent from `aggregate` and `per_query`
- A note is logged or printed explaining why context metrics are skipped (no ground truth for nfcorpus)

### 3.3 Missing API key

```bash
OPENAI_API_KEY="" uv run searchlab-eval ragas --dataset fiqa --slice 5
```

Expected: clear human-readable message (e.g. `Error: OPENAI_API_KEY is not set — skipping RAG eval`), exit code 0. No Python stack trace exposed.

### 3.4 Binary not found

```bash
# Temporarily rename the binary
mv ../searchlab ../searchlab.bak
uv run searchlab-eval ragas --dataset fiqa --slice 5
mv ../searchlab.bak ../searchlab
```

Expected: clear message that the `searchlab` binary was not found, non-zero exit. No hang.

### 3.5 Single query failure resilience

Verify by checking `rag_results.json` after a real 50-query run: if any queries were skipped (logged as warnings), the total entries in `rag_results.json` may be less than 50, and `rag_scores.json` reflects only the scored queries. The file should still be written and `aggregate` should still be present.

### 3.6 Web UI — Metrics tab, FiQA run with both panels

```bash
cd ..
./searchlab serve
```

1. Navigate to `http://localhost:8080#metrics`
2. Select the FiQA RAG run from the Run dropdown
3. Click Load

Expected:
- IR scores panel renders first (nDCG@10, Recall@10, MAP@10, etc.) as before
- RAG scores panel renders below it (Faithfulness, Answer Relevancy, Context Recall, Context Precision)
- Both panels visible simultaneously; no content is hidden or overwritten
- Clicking Load again with an IR-only run (no `rag_scores.json`) shows only the IR panel — RAG panel is hidden

### 3.7 Web UI — Eval tab, RAG Eval button

1. Navigate to `http://localhost:8080#eval`
2. Select dataset `FiQA-2018`
3. Enter slice `5` in the Slice field
4. Click the `RAG Eval` button

Expected:
- Log box opens and streams `uv run searchlab-eval ragas --dataset fiqa --slice 5` output
- Run completes and appears in the Available Runs table
- Run shows `Has Metrics` ✓ (or a new `Has RAG Metrics` indicator)

### 3.8 `rag_scores.json` shape validation

```bash
cat searchlab-eval/results/<run_id>/rag_scores.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'aggregate' in d
assert 'per_query' in d
assert 'measures' in d
assert all(m in d['aggregate'] for m in d['measures'])
print('Schema OK:', d['measures'])
"
```

Expected: `Schema OK: ['faithfulness', 'answer_relevancy', 'context_recall', 'context_precision']`

---

## 4. Constitution Checklist

| Rule | Check |
|------|-------|
| **Section IV — One Phase, One Win:** single objective met (first RAG quality numbers) | [ ] |
| **Section IV — LinkedIn post bullets exist** at `posts/phase-2.md` with the four FiQA scores | [ ] |
| **Section VI — Reproducibility:** `docker compose up` + README steps reach a working `ragas` run | [ ] |
| **Section VII — Spec discipline:** spec, plan, requirements, validation exist and are checked in | [ ] |
| **Section IX — No secrets in repo:** `SEARCHLAB_LLM_JUDGE_MODEL` in `.env.example` only | [ ] |
| **Section IX — README is current:** `ragas` command, new env var, and benchmark row documented | [ ] |

---

## 5. Merge Gate

All of the following must be true before opening a PR to main:

- [ ] Automated checks (§1) pass
- [ ] All AC rows (§2) marked pass
- [ ] All manual steps (§3) completed without unexpected failures
- [ ] Constitution checklist (§4) fully checked
- [ ] `rag_scores.json` for the FiQA 50-query run is committed alongside the code (the benchmark row is the evidence)
- [ ] `posts/phase-2.md` exists with the four FiQA scores and a plain-English read of each
- [ ] No open questions from `requirements.md` block the implementation (deferred ones logged in `backlog.md`)
- [ ] Phase 2 benchmark row added to `README.md` benchmark table

---

## 6. Known Deferred Items (not blockers)

Log in `backlog.md` if not already there:

- Averaging RAGAS scores across multiple runs to account for judge variance (currently single-run)
- Slice size power calculation — 50 queries is a convention, not a statistically motivated number
- Local judge model via Ollama (no marginal cost path)
- CI-gated regression on RAG scores (DeepEval candidate)
- Full four-metric nfcorpus run if reference answers are ever sourced
