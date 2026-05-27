# Phase 4 — IR Metrics: Validation

Conditions that confirm Phase 4 is correct and ready to merge.

---

## Manual checks

### 1. Basic metrics run

```bash
uv run searchlab-eval metrics ir --run-id $(ls results/ | grep nfcorpus | tail -1)
```

Pass: exits 0; prints a 7-row metric table to stdout; prints
`Metrics written to results/<run_id>/ir_scores.json`.

### 2. Output file well-formed

```bash
python3 -m json.tool results/nfcorpus-*/ir_scores.json | head -60
```

Pass: valid JSON; top-level keys are `run_id`, `dataset`, `computed_at`, `measures`,
`aggregate`, `per_query`. `aggregate` has exactly 7 entries. `per_query` is a non-empty
object.

### 3. Every query present in per_query

```bash
python3 - <<'EOF'
import json
from pathlib import Path

run_file = sorted(Path("results").glob("nfcorpus-*/raw_results.json"))[-1]
run_id = json.loads(run_file.read_text())["run_id"]

raw = json.loads(run_file.read_text())["results"]
scores_file = run_file.parent / "ir_scores.json"
per_query = json.loads(scores_file.read_text())["per_query"]

missing = [q for q in raw if q not in per_query]
print(f"Queries in run: {len(raw)}, missing from per_query: {len(missing)}")
if missing:
    print("FAIL — missing:", missing[:5])
else:
    print("PASS")
EOF
```

Pass: prints `PASS`.

### 4. Aggregate scores are non-trivially positive

```bash
python3 - <<'EOF'
import json
from pathlib import Path

scores_file = sorted(Path("results").glob("nfcorpus-*/ir_scores.json"))[-1]
agg = json.loads(scores_file.read_text())["aggregate"]
print("Aggregate scores:")
for k, v in agg.items():
    print(f"  {k:<16} {v:.4f}")

assert agg["ndcg_cut_10"] > 0.05, f"FAIL — ndcg_cut_10 suspiciously low: {agg['ndcg_cut_10']}"
print("PASS")
EOF
```

Pass: prints `PASS`; `ndcg_cut_10` is above 0.05 (sanity floor — real nfcorpus scores
are typically 0.30+).

### 5. Missing run directory error

```bash
uv run searchlab-eval metrics ir --run-id notexist-20990101T000000Z
```

Pass: exits non-zero; prints `Error: run not found at results/notexist-20990101T000000Z/raw_results.json — run 'searchlab-eval query' first`.
No Python traceback visible.

### 6. Missing qrels error

```bash
mkdir -p results/fake-run
echo '{"run_id":"fake","dataset":"nodataset","top_k":10,"created_at":"2026-01-01T00:00:00+00:00","results":{}}' \
  > results/fake-run/raw_results.json
uv run searchlab-eval metrics ir --run-id fake-run
```

Pass: exits non-zero; prints `Error: qrels not found at data/nodataset/qrels/test.tsv — run 'searchlab-eval download' first`.
No Python traceback visible.

Clean up: `rm -rf results/fake-run`.

### 7. All seven measures present in stdout table

```bash
uv run searchlab-eval metrics ir --run-id $(ls results/ | grep nfcorpus | tail -1) \
  | grep -c "ndcg_cut\|map_cut\|recall"
```

Pass: prints `7`.

### 8. `ir_scores.json` is gitignored

```bash
git status
```

Pass: `results/` directory does not appear in git status output (covered by existing
`.gitignore` entry).

---

## Automated checks

Run the unit tests (offline):

```bash
pytest tests/test_ir_metrics.py -v -m "not integration"
```

All seven unit tests pass.

Run the integration test (requires a completed nfcorpus query run):

```bash
pytest tests/test_ir_metrics.py -v -m integration
```

`test_metrics_ir_nfcorpus` passes.

---

## Manual verification record

Run each check above and record the result here before marking the completion gate.

Result values: `pass` / `fail` / `skip (reason)`.

### Check 1 — Basic metrics run

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 2 — Output file well-formed

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 3 — Every query present in per_query

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 4 — Aggregate scores non-trivially positive

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 5 — Missing run directory error

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 6 — Missing qrels error

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 7 — All seven measures in stdout

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

### Check 8 — ir_scores.json gitignored

| Result | Verified by | Date |
|--------|-------------|------|
| | | |

---

## Completion gate

- [ ] All eight manual checks pass
- [ ] `pytest tests/test_ir_metrics.py -m "not integration"` passes offline
- [ ] `pytest tests/test_ir_metrics.py -m integration` passes locally at least once
- [ ] `results/` absent from `git status` (`.gitignore` is effective)
- [ ] No import of any `searchlab` Python package anywhere in `searchlab_eval/`
- [ ] Roadmap `Phase 4` row updated to ✅
