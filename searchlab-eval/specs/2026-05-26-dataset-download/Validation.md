# Phase 1 — Dataset Download: Validation

Conditions that confirm Phase 1 is correct and ready to merge.

---

## Manual checks

### 1. Basic download
```
uv run searchlab-eval download --dataset nfcorpus
```
Pass: exits 0, prints a summary line, and `data/nfcorpus/` contains `corpus.jsonl`,
`queries.jsonl`, `qrels/test.tsv`.

### 2. Slice flag
```
uv run searchlab-eval download --dataset nfcorpus --slice 50
```
Pass: summary shows `→ 50 queries`. The file `data/nfcorpus/queries.jsonl` has exactly 50
lines.

### 3. Determinism
Run the slice command twice, capture the two `queries.jsonl` files:
```
uv run searchlab-eval download --dataset nfcorpus --slice 50
cp data/nfcorpus/queries.jsonl /tmp/q1.jsonl
uv run searchlab-eval download --dataset nfcorpus --slice 50
diff /tmp/q1.jsonl data/nfcorpus/queries.jsonl
```
Pass: `diff` prints nothing (files are identical).

### 4. Keep-all slice
```
uv run searchlab-eval download --dataset nfcorpus --slice 0
```
Pass: summary shows the full query count (≥ 1); no slice message.

### 5. Error on unknown dataset
```
uv run searchlab-eval download --dataset notadataset
```
Pass: exits non-zero, prints a human-readable error message, no Python traceback visible.

---

## Automated checks

Run the unit tests (offline):
```
pytest tests/test_download.py -v -m "not integration"
```
All four unit tests pass.

Run the integration test (requires network, run at least once locally before merging):
```
pytest tests/test_download.py -v -m integration
```
`test_download_nfcorpus` passes.

---

## Completion gate

- [ ] All five manual checks pass
- [ ] `pytest tests/test_download.py -m "not integration"` passes in CI (offline)
- [ ] `pytest tests/test_download.py -m integration` passes locally at least once
- [ ] `data/` absent from `git status` (`.gitignore` is effective)
- [ ] No import of `searchlab` Python package anywhere in `searchlab_eval/`
- [ ] Roadmap `Phase 1` row updated from plain text to ✅