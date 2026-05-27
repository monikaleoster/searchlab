# Phase 1 — Dataset Download: Plan

## Task Group 1 — downloader.py

1. Create `searchlab_eval/downloader.py`.
2. Implement `download_dataset(dataset_name: str, data_dir: Path) -> tuple[dict, dict, dict]`:
   - Use `beir.util.download_and_unzip` to fetch the dataset zip from the BEIR URL into
     `data_dir`.
   - Use `beir.datasets.data_loader.GenericDataLoader` to load and return
     `(corpus, queries, qrels)` in BEIR standard format.
   - `data_dir` defaults to `Path("data") / dataset_name` resolved from CWD.
3. Wrap the download call in a `try/except` and re-raise as a plain `RuntimeError` with a
   clear message on failure (e.g. network error, unknown dataset name).

## Task Group 2 — slicer.py

1. Create `searchlab_eval/slicer.py`.
2. Implement `slice_queries(queries: dict, qrels: dict, n: int) -> tuple[dict, dict]`:
   - Sort query IDs lexicographically (`sorted(queries.keys())`).
   - Take the first `n` IDs.
   - Return filtered `(queries, qrels)` containing only those IDs.
   - If `n == 0` or `n >= len(queries)`, return the full set unchanged.
3. No side effects — pure function operating on in-memory dicts.

## Task Group 3 — `download` CLI command

1. In `searchlab_eval/cli.py`, add a `download` Click command.
2. Options:
   - `--dataset` / `-d` (required): BEIR dataset name string.
   - `--slice` / `-s` (default 100): number of queries to keep; `0` keeps all.
3. Command flow:
   - Resolve `data_dir = Path("data") / dataset`.
   - Call `download_dataset(dataset, data_dir)` — catch `RuntimeError`, print message, exit 1.
   - If `--slice > 0`, call `slice_queries(queries, qrels, slice)`.
   - Write sliced `queries.jsonl` and `qrels/test.tsv` back to `data_dir`, overwriting the
     originals (corpus is never modified).
   - Print a one-line summary:
     `Downloaded {dataset}: {len(corpus)} docs, {original_q} → {final_q} queries`.

## Task Group 4 — smoke test

1. Create `tests/test_download.py`.
2. **Unit tests (no network)**:
   - `test_slice_determinism`: build a synthetic `queries` dict (20 entries), call
     `slice_queries` twice with `n=10`, assert both results are identical.
   - `test_slice_size`: assert returned dict has exactly `n` keys.
   - `test_slice_zero_keeps_all`: assert `slice_queries(q, r, 0)` returns all queries.
   - `test_slice_n_gte_total_keeps_all`: assert slice > total returns full set.
3. **Integration test** (requires network, tagged `@pytest.mark.integration`):
   - `test_download_nfcorpus(tmp_path)`: call `download_dataset("nfcorpus", tmp_path /
     "nfcorpus")`, assert `corpus.jsonl`, `queries.jsonl`, and `qrels/test.tsv` all exist
     and are non-empty.
4. Register `integration` mark in `pyproject.toml` under `[tool.pytest.ini_options]` to
   suppress the unknown-mark warning.