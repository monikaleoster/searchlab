# Validation — Python/FastAPI Migration

This document defines what "done" means for the Python migration and how to verify it. Complete all sections before merging to main and before deleting the Java code.

Prerequisites: `docker compose up` is running, FiQA and nfcorpus are indexed, `OPENAI_API_KEY` is set, `searchlab` service is running on port 8080.

---

## 1. Automated Checks

Run these first. Manual checks are irrelevant if these fail.

```bash
# searchlab Python package
cd searchlab
uv run pytest                          # unit tests

# searchlab-eval harness
cd ../searchlab-eval
uv run pytest                          # all existing tests (no regressions)
```

Pass criteria:
- [ ] `searchlab/` unit tests pass (chunker, context_builder, llm_client error paths)
- [ ] `searchlab-eval/` test suite exits 0 with no new failures compared to the Java baseline

---

## 2. Acceptance Criteria

| # | Criterion | How to verify | Pass | Fail |
|---|-----------|---------------|------|------|
| AC-1 | FastAPI service starts | `cd searchlab && uv run uvicorn searchlab.main:app --port 8080` | Server starts, `http://localhost:8080` loads | Startup error or blank page |
| AC-2 | `./searchlab rag` works | `./searchlab rag "what is dollar cost averaging"` against FiQA | Non-empty answer + at least one Source line | Error, empty output, or stack trace |
| AC-3 | `./searchlab query` works | `./searchlab query "vitamin D" --top-k 5` against nfcorpus | Ranked list of 5 results | Error or empty list |
| AC-4 | `./searchlab ingest` works | `./searchlab ingest test-corpus/sample.pdf` | Chunk count printed, no error | Error or 0 chunks |
| AC-5 | IR benchmark numbers match | Run full eval (see §3.3), compare to baseline | nDCG@10 within ±0.001 of Phase 0 | More than ±0.001 deviation |
| AC-6 | searchlab-eval ingest routes through REST | Run `searchlab-eval ingest --dataset fiqa` with searchlab service running | Ingested count printed, no OpenSearch connection from eval process | Eval still hits OpenSearch directly |
| AC-7 | searchlab-eval query routes through REST | Run `searchlab-eval query --dataset nfcorpus --slice 10` | `raw_results.json` written with doc_ids matching BEIR qrels | Empty results or missing doc_ids |
| AC-8 | Web UI all tabs functional | See §3.5 | All five tabs operate without JS errors | Any tab broken or blank |
| AC-9 | Java deleted after sign-off | `ls src/ pom.xml` after Group 9 | `No such file or directory` | Files still present |
| AC-10 | README reproducible | Follow README from scratch on a clean clone | Service starts and IR eval runs | Missing step or broken command |

---

## 3. Manual Verification Steps

### 3.1 CLI parity — rag command

Run the same questions against Java and Python back to back to confirm structural parity (not answer identity — LLM outputs vary):

```bash
# Python
./searchlab rag "what is dollar cost averaging"
./searchlab rag "what foods reduce cholesterol"
```

Expected for both:
- `Answer:` block followed by coherent text
- `Sources:` block with at least one `[N] filename  (score: X.XXX)` line
- Completes in under 35 seconds

### 3.2 CLI parity — query command

```bash
./searchlab query "what is a Roth IRA" --top-k 1
./searchlab query "what is a Roth IRA" --top-k 10
```

Expected:
- Ranked table or list format with rank, score, doc_id/filename
- `--top-k 1` shows exactly 1 result; `--top-k 10` shows up to 10

### 3.3 IR benchmark regression check

```bash
cd searchlab-eval

# FiQA
uv run searchlab-eval download --dataset fiqa --slice 50
uv run searchlab-eval ingest --dataset fiqa
uv run searchlab-eval query --dataset fiqa
uv run searchlab-eval metrics ir --run-id <run_id>
cat results/<run_id>/ir_scores.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('nDCG@10:', round(d['aggregate']['ndcg_cut_10'], 3))
print('Recall@10:', round(d['aggregate']['recall_10'], 3))
print('MAP@10:', round(d['aggregate']['map_cut_10'], 3))
"

# nfcorpus
uv run searchlab-eval download --dataset nfcorpus --slice 50
uv run searchlab-eval ingest --dataset nfcorpus
uv run searchlab-eval query --dataset nfcorpus
uv run searchlab-eval metrics ir --run-id <run_id>
```

Expected (within ±0.001 of Phase 0 baseline):

| Dataset | nDCG@10 | Recall@10 | MAP@10 |
|---------|---------|-----------|--------|
| FiQA-2018 | ~0.266 | ~0.342 | ~0.206 |
| nfcorpus | ~0.326 | ~0.139 | ~0.122 |

Deviations larger than ±0.001 indicate a bug in corpus indexing (likely `index_corpus_docs` field mapping).

### 3.4 Error handling

**Missing API key:**
```bash
OPENAI_API_KEY="" ./searchlab rag "test question"
```
Expected: clear message `OPENAI_API_KEY is not set`, non-zero exit, no stack trace.

**OpenSearch unavailable (stop docker-compose):**
```bash
./searchlab rag "what is compound interest"
```
Expected: human-readable connection error, non-zero exit. No raw Python traceback exposed.

**searchlab service unavailable (from eval):**
```bash
SEARCHLAB_URL="http://localhost:9999" uv run searchlab-eval query --dataset fiqa --slice 5
```
Expected: clear message naming `http://localhost:9999` as unreachable, non-zero exit.

**PDF not found:**
```bash
./searchlab ingest /does/not/exist.pdf
```
Expected: file not found message, non-zero exit.

### 3.5 Web UI — all tabs

Start the service and open `http://localhost:8080`.

**RAG tab:**
1. Select FiQA-2018 dataset
2. Enter "what is dollar cost averaging", click Ask
3. Verify: answer card appears with text and sources block

**Query tab:**
1. Select nfcorpus, enter "vitamin D deficiency", click Search
2. Verify: results table with rank, score, filename, snippet

**Ingest tab:**
1. Enter `test-corpus/sample.pdf`, click Ingest
2. Verify: success alert showing chunk count and index name

**Eval tab:**
1. Select FiQA-2018, enter slice 5
2. Click Download → log streams, completes with ✓ Done
3. Click Ingest → completes
4. Click Query → completes, run appears in Available Runs table
5. Enter run ID, click Compute Metrics → `ir_scores.json` written
6. Click RAG Eval → completes

**Metrics tab:**
1. Select a run with `ir_scores.json`, click Load
2. Verify IR aggregate grid renders (nDCG@10, Recall@10, MAP@10, etc.)
3. If a run with `rag_scores.json` exists: verify RAG panel renders below IR panel

### 3.6 Chunking equivalence spot-check

If both Java and Python have been used to index the same PDF, spot-check that the chunk count is the same:

```bash
# Python ingest
./searchlab ingest test-corpus/sample.pdf
# Note the chunk count printed

# Compare to what the Java version produced (if index was previously populated by Java)
# Check via: curl http://localhost:9200/searchlab-v0/_count
```

Expected: same chunk count within 0–1 (boundary token handling may differ by 1 at most).

### 3.7 `searchlab-eval` backward compat — deprecated `--opensearch-url`

```bash
uv run searchlab-eval ingest --dataset fiqa --opensearch-url http://localhost:9200
```
Expected: deprecation warning printed, command continues using `SEARCHLAB_URL` env var (not the passed OpenSearch URL). Does not error.

---

## 4. Constitution Checklist

| Rule | Check |
|------|-------|
| **Section IV — One Phase, One Win:** migration complete without retrieval or quality regressions | [ ] |
| **Section VI — Reproducibility:** `docker compose up` + README steps reach a working `./searchlab rag` | [ ] |
| **Section VII — Spec discipline:** spec, plan, requirements, validation checked in | [ ] |
| **Section IX — No secrets in repo:** all env vars in `.env.example` only | [ ] |
| **Section IX — README is current:** Java references removed; Python/uv steps documented | [ ] |
| **IR benchmark numbers unchanged:** `ir_scores.json` matches Phase 0 baseline within ±0.001 | [ ] |

---

## 5. Java Deletion Gate

Java code is deleted ONLY after all of the following are true:

- [ ] Automated checks (§1) pass
- [ ] All AC rows (§2) marked pass
- [ ] All manual steps (§3) completed without unexpected failures
- [ ] Constitution checklist (§4) fully checked
- [ ] IR benchmark regression confirmed (§3.3) — numbers match
- [ ] At least one full Phase 2 RAGAS run completes via the Python service (confirms end-to-end RAG works)

**Deletion commands (run only when gate is cleared):**
```bash
rm -rf src/ target/
rm pom.xml
git add -A
```

---

## 6. Known Deferred Items

Log in `backlog.md` if not already there:

- Async FastAPI routes (currently sync; blocking calls are fine for local dev use)
- Docker image for the `searchlab` service
- Real frontend (React/Svelte) to replace embedded HTML
- Authentication on FastAPI endpoints
- `--opensearch-url` deprecation alias removal (leave in for one phase)
- Streaming LLM responses in the RAG endpoint
