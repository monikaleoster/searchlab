# Phase 2 — Ingest: Requirements

## Context

Phase 1 is complete: `searchlab-eval download --dataset <name>` fetches and writes corpus,
queries, and qrels to `data/<dataset>/`. The corpus lives at `data/<dataset>/corpus.jsonl`
with one JSON object per line (`_id`, `title`, `text`).

This phase loads that corpus into OpenSearch so Phase 3 can run `searchlab query` against it.

## Deliverable

`searchlab-eval ingest --dataset scifact` reads `data/scifact/corpus.jsonl`, bulk-indexes
every document into the `searchlab-v0` OpenSearch index, and prints a summary of how many
docs landed.

## Scope

### In scope

- `searchlab_eval/ingestor.py` — read BEIR JSONL corpus, POST to OpenSearch `_bulk` endpoint,
  return doc count
- `ingest` sub-command added to `searchlab_eval/cli.py` (`--dataset`, `--opensearch-url` flags)
- Post-ingest doc count check via `GET /<index>/_count`
- Fail fast if OpenSearch is unreachable or any bulk batch returns errors
- Unit tests: bulk body format, batch splitting, missing-corpus error path
- Integration test (tagged `integration`): ingest nfcorpus against a live OpenSearch

### Out of scope

- Querying (Phase 3)
- Deleting or clearing the index before ingest — caller responsibility
- Schema migration — always targets the existing `searchlab-v0` index and mapping
- Retry logic on transient network errors

## Key design decisions

| Decision | Rationale |
|---|---|
| Use `requests` `_bulk` directly rather than `searchlab ingest` | `searchlab ingest` accepts a single PDF path and parses it page-by-page. BEIR corpus documents are plain text — there is no PDF conversion path. Direct HTTP bulk ingest is the only practical option. |
| `source_filename = beir_doc_id` | `searchlab query` surfaces `source_filename` in its output. Setting it to the BEIR doc ID gives Phase 3 the join key it needs to map ranked results back to qrels. |
| `chunk_text = title + " " + text` | The `searchlab-v0` BM25 search runs on `chunk_text`. Prepending the title to the body maximises recall for queries that match on title terms. |
| One document = one chunk | BEIR documents have no page or paragraph structure. Treating each doc as a single chunk avoids artificial fragmentation and keeps chunk-to-doc mapping trivial. |
| `chunk_id = page_number = chunk_position = 0` | Required by the `searchlab-v0` mapping; 0 is the correct sentinel for a single-chunk document. `chunk_id` is set to the BEIR doc ID for the same join-key reason as `source_filename`. |
| Batch size 500 | Keeps individual bulk request payloads under ~2 MB for typical BEIR doc lengths; small enough not to hit default OpenSearch limits. |
| `OPENSEARCH_URL` env var, default `http://localhost:9200` | Consistent with how the searchlab stack is configured; the CLI flag `--opensearch-url` overrides it. |

## Dependencies

- `requests>=2.28` — already declared in `pyproject.toml`; no new top-level dep needed
- Phase 1 download complete: `data/<dataset>/corpus.jsonl` must exist before running ingest

## Acceptance criteria

1. `searchlab-eval ingest --dataset nfcorpus` exits 0 and prints
   `Ingested <N> docs into searchlab-v0 (index total: <M>)`.
2. `<M>` matches `GET http://localhost:9200/searchlab-v0/_count` independently.
3. `searchlab-eval ingest --dataset notdownloaded` exits non-zero with a human-readable error
   (corpus file not found) — no Python traceback shown to the user.
4. `searchlab-eval ingest --dataset nfcorpus` with OpenSearch unreachable exits non-zero with
   a clear connection error message.
5. `pytest tests/test_ingest.py -m "not integration"` passes offline.
