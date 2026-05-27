# Phase 3 — Query: Requirements

## Context

Phase 2 is complete: `searchlab-eval ingest --dataset <name>` bulk-indexes the BEIR corpus
into OpenSearch. Each document is stored with `source_filename = beir_doc_id`, which gives
Phase 3 the join key it needs to map ranked results back to qrels.

The queries sliced by Phase 1 live at `data/<dataset>/queries.jsonl` — one JSON object per
line: `{"_id": "<query_id>", "text": "<query_text>"}`.

This phase iterates those queries, calls `searchlab query` for each one, parses the ranked
results, and writes them to disk in a format Phase 4 can feed directly to pytrec_eval.

## Deliverable

`searchlab-eval query --dataset scifact` runs every sliced query through `searchlab query`,
collects ranked results, and writes `results/<run_id>/raw_results.json`.

## Scope

### In scope

- `searchlab_eval/querier.py` — load `queries.jsonl`, call `searchlab query` per query via
  `subprocess.run`, parse the plain-text table output, accumulate results
- `query` sub-command in `searchlab_eval/cli.py`
  (`--dataset`, `--top-k`, `--opensearch-url` flags; `--run-id` output flag)
- `results/<run_id>/` directory creation; `raw_results.json` written there
- Progress bar via `tqdm` over the query loop
- Unit tests: output parser, no-results handling, missing queries file error path,
  `searchlab` not on PATH error path
- Integration test (tagged `integration`): run against live nfcorpus ingest

### Out of scope

- IR metrics (Phase 4)
- Parallel / async query execution — one query at a time is fine
- Caching or deduplication of query results across runs
- `results/latest/` symlink (introduced in Phase 6)

## Key design decisions

| Decision | Rationale |
|---|---|
| Parse `searchlab query` plain-text table output | `searchlab query` has no JSON or machine-readable output mode. Column-based regex parsing on the first four fields is sufficient given BEIR doc IDs contain no spaces. |
| `run_id = <dataset>-<YYYYMMDDTHHMMSSz>` | Human-readable, sortable, unique per invocation. Lets Phase 4–6 reference a run by name. The dataset prefix makes `ls results/` scannable. |
| Default `--top-k 10` | Phase 4 computes nDCG@{1,3,5,10}, MAP@10, Recall@{5,10}. Top-10 covers all required cut-offs without fetching unnecessary results. |
| Skip query on non-zero subprocess exit; log warning; continue | A single bad query should not abort a 100-query eval run. Phase 4 will see an empty list for that query, which scores 0 — correctly penalising the failure. |
| `raw_results.json` stores `(doc_id, score, rank)` per query | Score is needed for MAP; rank is a convenience for debugging. doc_id is the BEIR id, not the OpenSearch internal id. |
| `subprocess.run(..., capture_output=True, text=True)` | Keeps querier.py free of shell=True injection risk. `capture_output` gives clean stderr separation. |

## `raw_results.json` schema

```json
{
  "run_id": "nfcorpus-20260526T143025Z",
  "dataset": "nfcorpus",
  "top_k": 10,
  "created_at": "2026-05-26T14:30:25+00:00",
  "results": {
    "<query_id>": [
      {"doc_id": "<beir_doc_id>", "score": 0.6442, "rank": 1},
      ...
    ]
  }
}
```

Queries with zero results are present as empty lists (not omitted) so Phase 4 can
score them as rank-0 misses.

## `searchlab query` output format

The Java CLI prints a fixed-width table to stdout:

```
Rank  Score    Source                          Page  Snippet
----------------------------------------------------------------------------------------------------
1     0.6442   8430                            0     Oxygen therapy is ...
2     0.4716   7291                            0     Hypoxia in high ...
```

Format string (from `QueryCommand.java`):
```
%-4d  %-7.4f  %-30s  %-4d  %s
```

Parsing strategy: skip header and separator lines; for each data line apply the regex
`r'^(\d+)\s+([\d.]+)\s+(\S+)\s+(\d+)\s+(.*)$'` which captures rank, score, source
(BEIR doc ID — no spaces), page, and snippet. Only rank, score, and source are stored.

## Dependencies

- `tqdm>=4.66` — already declared in `pyproject.toml`; no new dep needed
- `searchlab` binary on `$PATH` — required at runtime; tested via `shutil.which("searchlab")`
- Phase 1 download complete: `data/<dataset>/queries.jsonl` must exist before querying
- Phase 2 ingest complete: documents must be in OpenSearch before querying

## Acceptance criteria

1. `searchlab-eval query --dataset nfcorpus` exits 0 and writes
   `results/nfcorpus-<timestamp>/raw_results.json` with a non-empty `results` dict.
2. Every query in `data/nfcorpus/queries.jsonl` appears as a key in `results` (even if
   the result list is empty).
3. `searchlab-eval query --dataset notdownloaded` exits non-zero with a clear error about
   missing queries file.
4. Running without `searchlab` on `$PATH` exits non-zero with a clear error message — no
   Python traceback visible.
5. `pytest tests/test_query.py -m "not integration"` passes offline.
