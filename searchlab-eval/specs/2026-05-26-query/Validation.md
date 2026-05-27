# Phase 3 — Query: Validation

Conditions that confirm Phase 3 is correct and ready to merge.

---

## Manual checks

### 1. Basic query run
### export PATH="/Users/monikaarora/code/searchlab:$PATH"
```bash
uv run searchlab-eval query --dataset nfcorpus
```

Pass: exits 0; prints `Queried <N> queries → results/nfcorpus-<timestamp>/raw_results.json`
where N > 0.

### 2. Output file well-formed

```bash
python3 -m json.tool results/nfcorpus-*/raw_results.json | head -40
```

Pass: valid JSON; top-level keys include `run_id`, `dataset`, `top_k`, `created_at`,
`results`; `results` is a non-empty object.

### 3. Every query present

```bash
python3 - <<'EOF'
import json
from pathlib import Path

queries = [json.loads(l)["_id"] for l in open("data/nfcorpus/queries.jsonl")]
run_file = sorted(Path("results").glob("nfcorpus-*/raw_results.json"))[-1]
results = json.loads(run_file.read_text())["results"]

missing = [q for q in queries if q not in results]
print(f"Total queries: {len(queries)}, missing from results: {len(missing)}")
if missing:
    print("FAIL — missing:", missing[:5])
else:
    print("PASS")
EOF
```

Pass: prints `PASS`.

### 4. Hit list is non-trivially populated

```bash
python3 - <<'EOF'
import json
from pathlib import Path

run_file = sorted(Path("results").glob("nfcorpus-*/raw_results.json"))[-1]
results = json.loads(run_file.read_text())["results"]
non_empty = sum(1 for v in results.values() if v)
total = len(results)
print(f"Queries with hits: {non_empty}/{total}")
assert non_empty > total * 0.5, "FAIL — fewer than half of queries returned hits"
print("PASS")
EOF
```

Pass: prints `PASS`; more than half of queries have at least one result.

### 5. Missing queries file error

```bash
uv run searchlab-eval query --dataset notdownloaded
```

Pass: exits non-zero; prints `Error: queries not found at data/notdownloaded/queries.jsonl — run download first`. No Python traceback visible.

### 6. searchlab not on PATH

```bash
PATH=/usr/bin uv run searchlab-eval query --dataset nfcorpus
```

Pass: exits non-zero; prints `Error: 'searchlab' not found on PATH …`. No Python
traceback visible.

### 7. Custom run-id is honoured

```bash
uv run searchlab-eval query --dataset nfcorpus --run-id my-test-run
ls results/my-test-run/
```

Pass: `raw_results.json` exists under `results/my-test-run/`.

### 8. results/ is gitignored

```bash
git status
```

Pass: `results/` directory does not appear in git status output.

---

## Automated checks

Run the unit tests (offline):

```bash
pytest tests/test_query.py -v -m "not integration"
```

All seven unit tests pass.

Run the integration test (requires running OpenSearch with nfcorpus ingested):

```bash
pytest tests/test_query.py -v -m integration
```

`test_query_nfcorpus` passes.

---

## Manual verification record

Run each check above and record the result here before marking the completion gate.

Result values: `pass` / `fail` / `skip (reason)`.

### Check 1 — Basic query run

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 2 — Output file well-formed

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 3 — Every query present

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 4 — Hit list non-trivially populated

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 5 — Missing queries file error

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 6 — searchlab not on PATH

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 7 — Custom run-id honoured

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 8 — results/ gitignored

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

---

## Completion gate

- [ ] All eight manual checks pass
- [ ] `pytest tests/test_query.py -m "not integration"` passes offline
- [ ] `pytest tests/test_query.py -m integration` passes locally at least once
- [ ] `results/` absent from `git status` (`.gitignore` is effective)
- [ ] No import of any `searchlab` Python package anywhere in `searchlab_eval/`
- [ ] Roadmap `Phase 2` row updated to ✅ and `Phase 3` row updated to ✅
