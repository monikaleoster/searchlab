# Phase 4 — IR Metrics: Plan

## Task Group 1 — `searchlab_eval/metrics/ir.py`

1. Create `searchlab_eval/metrics/__init__.py` (empty file — package marker only).

2. Create `searchlab_eval/metrics/ir.py`.

3. Declare the measures constant at module level:
   ```python
   MEASURES = {
       "ndcg_cut_1", "ndcg_cut_3", "ndcg_cut_5", "ndcg_cut_10",
       "map_cut_10",
       "recall_5", "recall_10",
   }
   ```

4. Implement `load_run(run_path: Path) -> tuple[str, str, dict[str, list[dict]]]`:
   - Raise `FileNotFoundError` if `run_path` does not exist.
   - Parse JSON; return `(data["run_id"], data["dataset"], data["results"])`.

5. Implement `load_qrels(qrels_path: Path) -> dict[str, dict[str, int]]`:
   - Raise `FileNotFoundError` if `qrels_path` does not exist.
   - Open the TSV; skip the header line (`query-id\tcorpus-id\tscore`).
   - For each row build `qrels[query_id][doc_id] = int(score)`.
   - Return the nested dict.

6. Implement `build_pytrec_run(results: dict[str, list[dict]]) -> dict[str, dict[str, float]]`:
   - For each `(query_id, hits)`, convert the list to `{hit["doc_id"]: hit["score"]}`.
   - Queries with empty hit lists map to `{}` — pytrec_eval will score them 0.
   - Return the nested dict.

7. Implement `compute_metrics(run: dict[str, dict[str, float]], qrels: dict[str, dict[str, int]]) -> dict[str, dict[str, float]]`:
   - Instantiate `pytrec_eval.RelevanceEvaluator(qrels, MEASURES)`.
   - Call `.evaluate(run)`; return the result directly.
   - Note: pytrec_eval only returns scores for query IDs present in the run dict. Queries not in qrels are silently skipped by pytrec_eval.

8. Implement `aggregate(per_query: dict[str, dict[str, float]]) -> dict[str, float]`:
   - For each measure in `MEASURES`, compute the arithmetic mean over all query scores.
   - Queries absent from `per_query` (not scored by pytrec_eval) contribute 0 to the mean only if there are queries in `run` but not in `per_query`; otherwise use the query count from `per_query`.
   - Return `{measure: mean_score}` for every measure in `MEASURES`, sorted by measure name.

9. Implement `format_table(aggregate: dict[str, float]) -> str`:
   - Produce a two-column plain-text table: `Metric` (left-aligned, 16 chars) and `Score` (right-aligned, 7 chars, `.4f`).
   - Include a separator line after the header.
   - Iterate measures in a fixed display order: `ndcg_cut_1`, `ndcg_cut_3`, `ndcg_cut_5`, `ndcg_cut_10`, `map_cut_10`, `recall_5`, `recall_10`.
   - Return the full string (caller prints it).

## Task Group 2 — `metrics ir` CLI command

1. In `searchlab_eval/cli.py`, add a `metrics` Click group:
   ```python
   @cli.group()
   def metrics() -> None:
       """Compute evaluation metrics for a completed run."""
   ```

2. Add an `ir` sub-command under `metrics`:
   ```python
   @metrics.command("ir")
   @click.option("--run-id", "-r", required=True, help="Run identifier (directory name under results/)")
   def metrics_ir(run_id: str) -> None:
   ```

3. Command flow:
   - Resolve `run_path = Path("results") / run_id / "raw_results.json"`.
   - If not present, print
     `Error: run not found at {run_path} — run 'searchlab-eval query' first`
     and exit 1.
   - Call `load_run(run_path)` to get `(_, dataset, results)`.
   - Resolve `qrels_path = Path("data") / dataset / "qrels" / "test.tsv"`.
   - If not present, print
     `Error: qrels not found at {qrels_path} — run 'searchlab-eval download' first`
     and exit 1.
   - Call `load_qrels(qrels_path)`.
   - Call `build_pytrec_run(results)`.
   - Call `compute_metrics(pytrec_run, qrels)`.
   - Call `aggregate(per_query_scores)`.
   - Build the output payload and write to `Path("results") / run_id / "ir_scores.json"`:
     ```python
     {
         "run_id": run_id,
         "dataset": dataset,
         "computed_at": datetime.now(timezone.utc).isoformat(),
         "measures": sorted(MEASURES),
         "aggregate": aggregated,
         "per_query": per_query_scores,
     }
     ```
   - Call `click.echo(format_table(aggregated))`.
   - Print: `Metrics written to results/{run_id}/ir_scores.json`.

4. Import guard: import `load_run`, `load_qrels`, `build_pytrec_run`, `compute_metrics`, `aggregate`, `format_table`, and `MEASURES` from `searchlab_eval.metrics.ir` inside the command function body (matches the lazy-import pattern used in `download` and `ingest`).

## Task Group 3 — tests

1. Create `tests/test_ir_metrics.py`.

2. **Unit tests (no subprocess, no disk I/O beyond tmp_path)**:

   - `test_load_run_missing_file`: assert `load_run(Path("nonexistent.json"))` raises
     `FileNotFoundError`.

   - `test_load_run_content(tmp_path)`: write a minimal `raw_results.json` to `tmp_path`;
     assert the returned tuple has the correct `run_id`, `dataset`, and `results` dict.

   - `test_load_qrels_missing_file`: assert `load_qrels(Path("nonexistent.tsv"))` raises
     `FileNotFoundError`.

   - `test_load_qrels_content(tmp_path)`: write a 3-row qrel TSV (including header);
     assert the returned dict has the correct structure and integer relevance values.

   - `test_build_pytrec_run`: pass a results dict with one non-empty and one empty hit list;
     assert the non-empty query maps to `{doc_id: score}` and the empty query maps to `{}`.

   - `test_aggregate_correct_mean`: pass a synthetic `per_query` dict with two queries and
     known scores for `ndcg_cut_10`; assert the aggregate mean is correct to 4 decimal places.

   - `test_format_table_contains_all_measures`: call `format_table` with a dummy aggregate
     dict (all zeros); assert the returned string contains all seven measure names.

3. **Integration test** (tagged `@pytest.mark.integration`, requires a completed nfcorpus
   query run):

   - `test_metrics_ir_nfcorpus(tmp_path)`: skip if
     `results/` contains no `nfcorpus-*/raw_results.json`; load the most recent such file;
     call the full pipeline (`load_run` → `load_qrels` → `build_pytrec_run` →
     `compute_metrics` → `aggregate`); assert `ndcg_cut_10 > 0` and all seven measures
     are present in the aggregate dict.

## Task Group 4 — housekeeping

1. Update `roadmap.md`: change `## Phase 4 — IR metrics` to `## Phase 4 — IR metrics ✅`
   once validation passes.
