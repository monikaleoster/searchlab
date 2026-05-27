# Phase 1 — Dataset Download: Requirements

## Context

Phase 0 scaffold is complete: `uv run searchlab-eval --help` works, the CLI entry point and
package structure are in place.

This phase delivers the first real capability: fetching a BEIR benchmark dataset from the
internet, writing it to a well-known local path, and optionally slicing it to a smaller query
set for fast iteration.

## Deliverable

`searchlab-eval download --dataset scifact` fetches corpus, queries, and qrels into
`data/scifact/`.

## Scope

### In scope

- `searchlab_eval/downloader.py` — wrap BEIR `GenericDataLoader` to download any named BEIR
  dataset
- `searchlab_eval/slicer.py` — deterministic slice of the query set to N queries by sorted
  query ID
- `download` sub-command added to `searchlab_eval/cli.py` (`--dataset`, `--slice` flags)
- Smoke test: download `nfcorpus` (smallest BEIR dataset), assert expected file counts and
  slicer determinism

### Out of scope

- Ingest into OpenSearch (Phase 2)
- Querying or metrics (Phases 3–5)
- Network retry logic beyond what BEIR already provides
- Any modification to the corpus — only queries and qrels are sliced

## Key decisions

| Decision | Rationale |
|---|---|
| Use BEIR `GenericDataLoader` | Handles HTTP download, zip extraction, and the standard `corpus.jsonl` / `queries.jsonl` / `qrels/` layout. No re-implementation needed. |
| Slice by sorted query ID (lexicographic) | Determinism: the same `--slice 50` always produces the same 50 queries regardless of runtime state. |
| Default slice = 100 | Keeps a local run under 5 minutes while covering enough queries for stable nDCG estimates. |
| Slice `--slice 0` means keep all | Explicit opt-out; avoids ambiguity about "no slice" vs "zero queries". |
| Data path = `data/<dataset>/` relative to CWD | Matches the `.gitignore` exclusion declared in Phase 0; keeps downloaded data out of the repo. |
| `nfcorpus` for smoke test | Smallest BEIR dataset (~3 500 docs); downloads in seconds, safe for local CI. |

## Dependencies

- `beir` library declared in `pyproject.toml`
- Python 3.12, `uv` for running

## Acceptance criteria

1. `searchlab-eval download --dataset nfcorpus` exits 0 and writes `corpus.jsonl`,
   `queries.jsonl`, and `qrels/test.tsv` under `data/nfcorpus/`.
2. `searchlab-eval download --dataset nfcorpus --slice 50` produces exactly 50 query entries.
3. Two runs with `--slice 50` produce identical `queries.jsonl` files (determinism).
4. `searchlab-eval download --dataset notadataset` exits non-zero with a human-readable error
   — no Python traceback shown to the user.
5. `pytest tests/test_download.py` passes; non-integration tests pass without network access.