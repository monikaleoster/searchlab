# Tech Stack

## Language

**Python 3.12** — matches the searchlab-eval venv already in place.

## Dependency management

**uv** — fast, deterministic installs. All dev and prod deps declared in `pyproject.toml`.

## Core libraries

### Dataset

| Library | Role |
|---|---|
| `beir` | Download BEIR benchmark datasets (corpus, queries, qrels). Handles HTTP, extraction, and standard format. |

BEIR datasets are written to `./data/<dataset>/` and committed to `.gitignore`. A `--slice N` flag subsets queries deterministically (by sorted query ID) so partial runs are reproducible.

### IR metrics

| Library | Role |
|---|---|
| `pytrec_eval` | Python bindings for trec_eval. Computes nDCG@k, MAP@k, Recall@k, MRR@k against BEIR qrels. Ground truth is the BEIR qrel file; ranked results come from searchlab query output. |

Metric sweep defaults: `k ∈ {1, 3, 5, 10}`. All raw per-query scores written to `results/<run_id>/ir_scores.json` before aggregation.

### RAG metrics

| Library | Role |
|---|---|
| `ragas` | Faithfulness, answer relevancy, context recall. Requires an LLM judge (configurable via `RAGAS_LLM` env var, defaults to `claude-haiku-4-5`). |

RAG metrics are optional — skipped if `--rag` flag is not passed, so IR-only runs have no LLM cost.

### Reporting

| Library | Role |
|---|---|
| `pandas` | Aggregates per-query scores into summary DataFrames for the report. |
| `Jinja2` | Renders a single self-contained `.html` file (inline CSS, no external deps). Open with any browser. |

The report is written to `results/<run_id>/report.html`. The last run's report is also symlinked to `results/latest/report.html`.

### Test harness

| Library | Role |
|---|---|
| `pytest` | Wraps an eval run as a test. Thresholds declared in `eval_thresholds.toml`. A metric below threshold fails the test. |

Example threshold config:
```toml
[thresholds]
ndcg_at_10 = 0.45
recall_at_10 = 0.60
```

### CLI

| Library | Role |
|---|---|
| `click` | Entry-point CLI (`searchlab-eval run`, `searchlab-eval report`, `searchlab-eval list`). |

## External dependencies (runtime, not Python)

| Dependency | How used |
|---|---|
| `searchlab` CLI on `$PATH` | Called via `subprocess` for `ingest` and `query`. Version pinned in `eval_thresholds.toml`. |
| Running OpenSearch | Target for ingest and query. URL configured via `OPENSEARCH_URL` env var (default `http://localhost:9200`). |

## What is deliberately excluded

- No direct OpenSearch Python client — all search I/O goes through the `searchlab` CLI.
- No FastAPI / web server — the HTML report is a static file, not a running service.
- No LLM SDK imports at the top level — ragas brings its own; the eval module does not import `anthropic` directly.