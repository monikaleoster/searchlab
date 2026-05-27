# Phase 3 — Query: Plan

## Task Group 1 — querier.py

1. Create `searchlab_eval/querier.py`.

2. Implement `_parse_hits(stdout: str) -> list[dict]`:
   - Skip the header line (`Rank  Score ...`) and the separator line (`---...`).
   - For each remaining non-empty line, apply:
     `HIT_RE = re.compile(r'^(\d+)\s+([\d.]+)\s+(\S+)\s+(\d+)\s+(.*)$')`
   - If the line matches, append `{"doc_id": group(3), "score": float(group(2)), "rank": int(group(1))}`.
   - If the line is the `"No results found for: ..."` sentinel, return `[]`.
   - Return the collected list (empty list if no hits).

3. Implement `run_query(query_text: str, opensearch_url: str, top_k: int) -> list[dict]`:
   - Build the command: `["searchlab", "query", query_text, "--top-k", str(top_k)]`.
   - Set env: pass current environment plus `OPENSEARCH_URL=opensearch_url`.
   - Call `subprocess.run(cmd, capture_output=True, text=True, env=env)`.
   - If return code is non-zero, raise `RuntimeError(f"searchlab query exited {proc.returncode}: {proc.stderr.strip()}")`.
   - Return `_parse_hits(proc.stdout)`.

4. Implement `load_queries(queries_path: Path) -> dict[str, str]`:
   - Raise `FileNotFoundError` if `queries_path` does not exist.
   - Read each line as JSON; build and return `{obj["_id"]: obj["text"]}`.

5. Implement `run_queries(queries: dict[str, str], opensearch_url: str, top_k: int) -> dict[str, list[dict]]`:
   - Wrap the loop in `tqdm(queries.items(), desc="Querying", unit="q")`.
   - For each `(query_id, text)`, call `run_query(text, opensearch_url, top_k)`.
   - On `RuntimeError`, log `f"Warning: query {query_id!r} failed: {e}"` to stderr and store `[]`.
   - Return `{query_id: hits_list}` for all queries (including empty-result ones).

## Task Group 2 — `query` CLI command

1. In `searchlab_eval/cli.py`, add a `query` Click command.

2. Options:
   - `--dataset` / `-d` (required): BEIR dataset name.
   - `--top-k` / `-k`: default `10`, minimum number of results per query.
   - `--opensearch-url` / `-u`: default reads `OPENSEARCH_URL` env var, falls back to
     `http://localhost:9200`. Use `click.option(..., envvar="OPENSEARCH_URL")`.
   - `--run-id`: optional string; if omitted, generate as `f"{dataset}-{utc_timestamp}"`.

3. Command flow:
   - Check `shutil.which("searchlab")` — if `None`, print
     `Error: 'searchlab' not found on PATH — build the JAR and ensure ./searchlab is executable`
     and exit 1.
   - Resolve `queries_path = Path("data") / dataset / "queries.jsonl"`.
   - If not present, print `Error: queries not found at {queries_path} — run download first`
     and exit 1.
   - Call `load_queries(queries_path)`.
   - Generate `run_id` if not provided: `f"{dataset}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"`.
   - Create `results_dir = Path("results") / run_id`; call `results_dir.mkdir(parents=True, exist_ok=True)`.
   - Call `run_queries(queries, opensearch_url, top_k)`.
   - Build the output payload and write it to `results_dir / "raw_results.json"`:
     ```python
     {
       "run_id": run_id,
       "dataset": dataset,
       "top_k": top_k,
       "created_at": datetime.now(timezone.utc).isoformat(),
       "results": results,
     }
     ```
   - Print: `Queried {len(queries)} queries → results/{run_id}/raw_results.json`.

## Task Group 3 — tests

1. Create `tests/test_query.py`.

2. **Unit tests (no subprocess)**:

   - `test_parse_hits_normal`: pass a two-line result string matching the `searchlab query`
     format; assert returned list has 2 items with correct `doc_id`, `score`, and `rank`.

   - `test_parse_hits_no_results`: pass the sentinel string
     `"No results found for: some query"`; assert the function returns `[]`.

   - `test_parse_hits_empty_output`: pass an empty string (or only header/separator lines);
     assert returns `[]`.

   - `test_load_queries_missing_file`: assert `load_queries(Path("nonexistent.jsonl"))`
     raises `FileNotFoundError`.

   - `test_load_queries_content(tmp_path)`: write 3 synthetic query lines to a temp file;
     assert `load_queries` returns the correct `{id: text}` dict.

   - `test_run_query_nonzero_exit`: mock `subprocess.run` to return a `CompletedProcess`
     with `returncode=1` and `stderr="connection refused"`; assert `run_query` raises
     `RuntimeError` containing `"exited 1"`.

   - `test_run_queries_continues_on_error`: mock `run_query` to raise `RuntimeError` for
     one of two queries; assert `run_queries` returns results for both query IDs (the
     failing one as `[]`).

3. **Integration test** (tagged `@pytest.mark.integration`, requires running OpenSearch and
   a pre-ingested nfcorpus):

   - `test_query_nfcorpus(tmp_path)`: skip if `data/nfcorpus/queries.jsonl` absent; call
     `load_queries` then `run_queries` with `top_k=5` on a 3-query slice; assert every
     query ID is present in the result dict; assert at least one result list is non-empty.

## Task Group 4 — housekeeping

1. Confirm `results/` is listed in `.gitignore` (add if missing).
2. Update `roadmap.md`: change `## Phase 2 — Ingest` to `## Phase 2 — Ingest ✅` and
   `## Phase 3 — Query` header to `## Phase 3 — Query ✅` once validation passes.
