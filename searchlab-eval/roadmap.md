# Roadmap

Each phase is ~1–2 days of work and ships a locally runnable artifact. Every phase leaves the repo in a working state — no half-finished phases committed.

---

## Phase 0 — Scaffold ✅
**Deliverable:** `uv run searchlab-eval --help` works.

- `pyproject.toml` with all deps declared
- `searchlab_eval/` package with `cli.py` entry point (click)
- `uv.lock` committed
- `tests/` directory with one smoke test
- `.gitignore` covering `data/`, `results/`, `.venv/`

---

## Phase 1 — Dataset download ✅
**Deliverable:** `searchlab-eval download --dataset scifact` fetches and writes corpus/queries/qrels to `data/scifact/`.

- `downloader.py`: wrap BEIR `GenericDataLoader`
- `slicer.py`: deterministic slice to N queries by sorted query ID (`--slice N`, default 100)
- Smoke test: download nfcorpus (smallest BEIR dataset), assert file counts

---

## Phase 2 — Ingest
**Deliverable:** `searchlab-eval ingest --dataset scifact` calls `searchlab ingest` and reports how many docs landed in OpenSearch.

- `ingestor.py`: build ingest CLI args from corpus path, call via `subprocess.run`
- Post-ingest doc count check against OpenSearch `_count` endpoint
- Fail fast with clear error if OpenSearch is unreachable or ingest exits non-zero

---

## Phase 3 — Query
**Deliverable:** `searchlab-eval query --dataset scifact` runs all sliced queries through `searchlab query` and writes ranked results to `results/<run_id>/raw_results.json`.

- `querier.py`: iterate queries, call `searchlab query "<text>"` per query, parse stdout JSON
- Store results in TREC run format (query_id → [(doc_id, score), …])
- Progress bar (tqdm) so local runs feel responsive

---

## Phase 4 — IR metrics
**Deliverable:** `searchlab-eval metrics ir --run-id <id>` prints a metrics table and writes `ir_scores.json`.

- `metrics/ir.py`: load `raw_results.json` + qrels, run pytrec_eval for nDCG@{1,3,5,10}, MAP@10, Recall@{5,10}
- Aggregate mean scores across queries
- Write `results/<run_id>/ir_scores.json`
- Pretty-print table to stdout

---

## Phase 5 — RAG metrics
**Deliverable:** `searchlab-eval metrics rag --run-id <id>` adds faithfulness, answer relevancy, context recall to the run.

- `metrics/rag.py`: call ragas with retrieved contexts and generated answers from `raw_results.json`
- LLM judge configured via `RAGAS_LLM` env var
- Gate behind `--rag` flag — no-op (and no LLM cost) if flag absent
- Write `results/<run_id>/rag_scores.json`

---

## Phase 6 — HTML report
**Deliverable:** `searchlab-eval report --run-id <id>` opens `results/<run_id>/report.html` in the browser.

- `reporter.py`: load ir_scores.json (and rag_scores.json if present), build pandas DataFrames
- Jinja2 template: summary scorecard at top, per-query breakdown table below, pass/fail badges vs thresholds
- Single self-contained `.html` (inline CSS, no CDN — works fully offline)
- `results/latest/report.html` symlink updated on every run
- `--open` flag calls `webbrowser.open()` automatically

---

## Phase 7 — End-to-end CLI command
**Deliverable:** `searchlab-eval run --dataset scifact --slice 50` executes phases 1–6 in sequence and opens the report.

- `run.py`: orchestrate download → ingest → query → IR metrics → (optionally) RAG metrics → report
- Single config file `eval_config.toml` for dataset, slice size, thresholds, OpenSearch URL
- Exit code 0 if all metrics meet thresholds, non-zero otherwise (CI-friendly)

---

## Phase 8 — CI / pytest harness
**Deliverable:** `pytest searchlab-eval/` passes in CI and fails when metrics drop below thresholds in `eval_thresholds.toml`.

- `tests/test_eval_thresholds.py`: run eval (with a tiny slice for speed), assert each metric ≥ threshold
- `eval_thresholds.toml` committed; tuned thresholds updated here when intentional regressions are accepted
- GitHub Actions workflow snippet in `ci/eval.yml`

---

## Out of scope (not in this roadmap)

- Live dashboard / streaming results
- Multi-index or multi-config comparison in one run (deferred — single run per invocation)
- Direct OpenSearch SDK usage (always via `searchlab` CLI)
- Automatic threshold tuning