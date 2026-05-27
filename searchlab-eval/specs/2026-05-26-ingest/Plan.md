# Phase 2 — Ingest: Plan

## Task Group 1 — ingestor.py

1. Create `searchlab_eval/ingestor.py`.

2. Implement `_build_bulk_body(docs: list[dict], ingested_at: str) -> str`:
   - `docs` is a list of BEIR corpus entries: `{"_id": str, "title": str, "text": str}`.
   - For each doc emit two NDJSON lines:
     - Action line: `{"index": {"_index": "searchlab-v0", "_id": "<_id>"}}`
     - Document line: `{"chunk_id": _id, "chunk_text": title + " " + text, "source_filename": _id, "page_number": 0, "chunk_position": 0, "ingested_at": ingested_at}`
   - Return the full NDJSON string (trailing newline required by `_bulk`).

3. Implement `ingest_corpus(corpus_path: Path, opensearch_url: str, batch_size: int = 500) -> int`:
   - Raise `FileNotFoundError` if `corpus_path` does not exist.
   - Read `corpus_path` line-by-line; parse each as JSON.
   - Group into batches of `batch_size`.
   - For each batch, call `_post_bulk(opensearch_url, _build_bulk_body(batch, ingested_at))`.
   - Accumulate and return total docs indexed across all batches.

4. Implement `_post_bulk(opensearch_url: str, body: str) -> None`:
   - POST to `<opensearch_url>/_bulk` with `Content-Type: application/x-ndjson`.
   - On `requests.exceptions.ConnectionError`, raise `RuntimeError("OpenSearch unreachable at <url>")`.
   - On non-2xx HTTP status, raise `RuntimeError` with the status code and first 200 chars of the response body.
   - If `response.json()["errors"]` is `True`, collect the first failing item's reason and raise `RuntimeError`.

5. Implement `get_doc_count(opensearch_url: str, index: str = "searchlab-v0") -> int`:
   - GET `<opensearch_url>/<index>/_count`.
   - On `ConnectionError` or non-2xx, raise `RuntimeError` with a clear message.
   - Return `response.json()["count"]`.

## Task Group 2 — `ingest` CLI command

1. In `searchlab_eval/cli.py`, add an `ingest` Click command.

2. Options:
   - `--dataset` / `-d` (required): BEIR dataset name.
   - `--opensearch-url` / `-u`: default reads `OPENSEARCH_URL` env var, falls back to
     `http://localhost:9200`. Use `click.option(..., envvar="OPENSEARCH_URL")`.

3. Command flow:
   - Resolve `corpus_path = Path("data") / dataset / "corpus.jsonl"`.
   - If `corpus_path` does not exist, print `Error: corpus not found at <path> — run download first` and exit 1.
   - Call `ingest_corpus(corpus_path, opensearch_url)` — catch `RuntimeError`, print the message, exit 1.
   - Call `get_doc_count(opensearch_url)` — catch `RuntimeError`, print `Warning: could not verify doc count: <msg>` and continue.
   - Print: `Ingested {n_ingested} docs into searchlab-v0 (index total: {n_count})`.

## Task Group 3 — tests

1. Create `tests/test_ingest.py`.

2. **Unit tests (no network)** — patch `requests.post` / `requests.get` in all cases:

   - `test_bulk_body_format`: call `_build_bulk_body` with 2 synthetic docs; assert the
     resulting NDJSON lines contain the correct `chunk_id`, `chunk_text` (title + space + text),
     `source_filename`, `page_number = 0`, and `chunk_position = 0`.

   - `test_batch_splitting`: write a 1 200-line synthetic `corpus.jsonl` to `tmp_path`; mock
     `_post_bulk` to record calls; assert `ingest_corpus` makes exactly 3 calls
     (`ceil(1200 / 500) = 3`) and returns 1200.

   - `test_missing_corpus_raises`: assert `ingest_corpus(Path("nonexistent.jsonl"), ...)` raises
     `FileNotFoundError`.

   - `test_opensearch_unreachable`: mock `requests.post` to raise
     `requests.exceptions.ConnectionError`; assert `ingest_corpus` raises `RuntimeError`
     containing "unreachable".

   - `test_bulk_errors_raise`: mock `requests.post` to return a response with
     `{"errors": true, "items": [{"index": {"error": {"reason": "mapping error"}}}]}`; assert
     `RuntimeError` is raised.

3. **Integration test** (tagged `@pytest.mark.integration`, requires running OpenSearch):

   - `test_ingest_nfcorpus(tmp_path)`: skip if `data/nfcorpus/corpus.jsonl` is absent (use
     `pytest.importorskip` or a `skipif` on path existence); call
     `ingest_corpus("data/nfcorpus/corpus.jsonl", "http://localhost:9200")`; assert returned
     count > 0; call `get_doc_count`; assert index total ≥ returned count.
