# Phase 2 — Ingest: Validation

Conditions that confirm Phase 2 is correct and ready to merge.

---

## Manual checks

### 1. Basic ingest
```
uv run searchlab-eval ingest --dataset nfcorpus
```
Pass: exits 0, prints `Ingested <N> docs into searchlab-v0 (index total: <M>)` where both
numbers are > 0 and M ≥ N.

### 2. Doc count agreement
```
curl -s http://localhost:9200/searchlab-v0/_count | python3 -m json.tool
```
Pass: `"count"` matches `<M>` printed by the ingest command.

### 3. Source filename is BEIR doc ID
```
uv run searchlab query "oxygen" --top-k 3
```
Pass: the `Source` column shows strings that look like BEIR doc IDs (e.g. `8430` for
nfcorpus), not filenames ending in `.pdf`.

### 4. Missing corpus error
```
uv run searchlab-eval ingest --dataset notdownloaded
```
Pass: exits non-zero, prints `Error: corpus not found at data/notdownloaded/corpus.jsonl — run download first`. No Python traceback visible.

### 5. OpenSearch unreachable
```
uv run searchlab-eval ingest --dataset nfcorpus --opensearch-url http://localhost:19200
```
Pass: exits non-zero, prints a clear connection error message. No Python traceback visible.

### 6. OPENSEARCH_URL env var
```
OPENSEARCH_URL=http://localhost:9200 uv run searchlab-eval ingest --dataset nfcorpus
```
Pass: behaves identically to check 1 — env var is picked up without the `--opensearch-url` flag.

---

## Automated checks

Run the unit tests (offline):
```
pytest tests/test_ingest.py -v -m "not integration"
```
All five unit tests pass.

Run the integration test (requires running OpenSearch):
```
pytest tests/test_ingest.py -v -m integration
```
`test_ingest_nfcorpus` passes.

---

## Manual verification record

Run each check above and record the result here before marking the completion gate.

Result values: `pass` / `fail` / `skip (reason)`.

### Check 1 — Basic ingest

1. Ensure OpenSearch is running (`curl -s http://localhost:9200` returns JSON).
2. Run `uv run searchlab-eval ingest --dataset nfcorpus`.
3. Confirm exit code 0: `echo $?` → `0`.
4. Confirm output contains `Ingested <N> docs into searchlab-v0 (index total: <M>)` with both N and M > 0 and M ≥ N.

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 2 — Doc count agreement

1. Note the `<M>` value printed by Check 1.
2. Run `curl -s http://localhost:9200/searchlab-v0/_count | python3 -m json.tool`.
3. Confirm `"count"` in the JSON equals `<M>`.

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 3 — Source filename is BEIR doc ID

1. Run `uv run searchlab query "oxygen" --top-k 3`.
2. Inspect the `Source` column in the output.
3. Confirm values are BEIR doc IDs (e.g. `8430`), not paths ending in `.pdf`.

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 4 — Missing corpus error

1. Run `uv run searchlab-eval ingest --dataset notdownloaded`.
2. Confirm exit code is non-zero: `echo $?` → non-`0`.
3. Confirm output contains `Error: corpus not found at data/notdownloaded/corpus.jsonl — run download first`.
4. Confirm no Python traceback appears in the output.

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 5 — OpenSearch unreachable

1. Run `uv run searchlab-eval ingest --dataset nfcorpus --opensearch-url http://localhost:19200`.
2. Confirm exit code is non-zero: `echo $?` → non-`0`.
3. Confirm output contains a clear connection error message.
4. Confirm no Python traceback appears in the output.

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 6 — OPENSEARCH_URL env var

1. Run `OPENSEARCH_URL=http://localhost:9200 uv run searchlab-eval ingest --dataset nfcorpus`.
2. Confirm behavior is identical to Check 1 (same exit code, same output format).
3. Confirm no `--opensearch-url` flag was needed.

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

---

## Completion gate

- [ ] All six manual checks pass
- [ ] `pytest tests/test_ingest.py -m "not integration"` passes offline
- [ ] `pytest tests/test_ingest.py -m integration` passes locally at least once
- [ ] `data/` absent from `git status` (`.gitignore` is effective)
- [ ] No import of any `searchlab` Python package anywhere in `searchlab_eval/`
- [ ] Roadmap `Phase 2` row updated from plain text to ✅
