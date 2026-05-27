# Phase 4 — IR Metrics: Requirements

## Context

Phase 3 is complete: `searchlab-eval query --dataset <name>` runs all sliced queries through
`searchlab query` and writes ranked results to `results/<run_id>/raw_results.json`.

Each entry in `results` maps a query ID to an ordered list of
`{"doc_id": "<beir_doc_id>", "score": <float>, "rank": <int>}` objects. Queries with zero
hits are stored as empty lists (not omitted).

The BEIR relevance judgements (qrels) are written by Phase 1 to
`data/<dataset>/qrels/test.tsv` — a TSV with header `query-id\tcorpus-id\tscore` where
`score` is an integer relevance label (0 = not relevant, 1 = relevant, 2 = highly relevant
for multi-graded datasets).

This phase loads both artifacts, runs them through `pytrec_eval`, aggregates per-query
scores into means, and writes `results/<run_id>/ir_scores.json`. It also pretty-prints a
summary table to stdout.

## Deliverable

`searchlab-eval metrics ir --run-id <id>` computes nDCG, MAP, and Recall against BEIR qrels
and writes `results/<run_id>/ir_scores.json`.

## Scope

### In scope

- `searchlab_eval/metrics/__init__.py` — empty package marker
- `searchlab_eval/metrics/ir.py` — load artifacts, call pytrec_eval, aggregate, format
- `metrics ir` sub-command in `searchlab_eval/cli.py` (via a `metrics` Click group)
- `results/<run_id>/ir_scores.json` written with per-query and aggregate scores
- Pretty-printed table to stdout (plain text, no external rendering dep)
- Unit tests: qrel loader, metric aggregation, output schema
- Integration test (tagged `integration`): run against a real nfcorpus run

### Out of scope

- RAG metrics (Phase 5)
- Threshold enforcement / CI gating (Phase 8)
- HTML report rendering (Phase 6)
- MRR metrics — not required by the roadmap cut-offs
- Multi-run comparison in one invocation

## Key design decisions

| Decision | Rationale |
|---|---|
| `pytrec_eval.RelevanceEvaluator` with explicit measure set | Only the required cut-offs are computed; avoids computing the full trec_eval battery. Measure strings map directly to JSON output keys for traceability. |
| Measures: `ndcg_cut_1`, `ndcg_cut_3`, `ndcg_cut_5`, `ndcg_cut_10`, `map_cut_10`, `recall_5`, `recall_10` | Matches the roadmap specification. nDCG@10 is the primary headline metric; MAP@10 and Recall@{5,10} provide complementary signal on ranking quality and coverage. |
| Per-query scores stored alongside aggregate | Phase 6 (HTML report) needs per-query breakdown for the query-level table. Writing them now avoids a re-compute step later. |
| `metrics` Click group with `ir` sub-command | Mirrors the roadmap shape (`metrics ir`, `metrics rag`). Keeps `cli.py` extensible without restructuring for Phase 5. |
| Aggregate = arithmetic mean over queries | Standard TREC reporting convention. Queries with empty result lists score 0 on all metrics — correctly penalising failures as per the Phase 3 design decision. |
| qrels cast to `int` | pytrec_eval requires integer relevance grades. BEIR TSV scores are already integers but are read as strings by `csv.reader`; explicit cast guards against edge cases. |
| Plain-text table printed with `click.echo` | `rich` and `tabulate` are not in `pyproject.toml`. Pandas is available but overkill for a 7-row table. Simple f-string column alignment is sufficient and has no extra dep cost. |

## `ir_scores.json` schema

```json
{
  "run_id": "nfcorpus-20260526T143025Z",
  "dataset": "nfcorpus",
  "computed_at": "2026-05-26T14:32:00+00:00",
  "measures": ["ndcg_cut_1", "ndcg_cut_3", "ndcg_cut_5", "ndcg_cut_10", "map_cut_10", "recall_5", "recall_10"],
  "aggregate": {
    "ndcg_cut_1":  0.3012,
    "ndcg_cut_3":  0.3540,
    "ndcg_cut_5":  0.3801,
    "ndcg_cut_10": 0.4150,
    "map_cut_10":  0.3321,
    "recall_5":    0.4600,
    "recall_10":   0.5900
  },
  "per_query": {
    "<query_id>": {
      "ndcg_cut_1":  0.0,
      "ndcg_cut_3":  0.4226,
      "ndcg_cut_5":  0.4512,
      "ndcg_cut_10": 0.5000,
      "map_cut_10":  0.4000,
      "recall_5":    0.5000,
      "recall_10":   0.7500
    }
  }
}
```

## pytrec_eval interface

```python
import pytrec_eval

# qrels: {query_id: {doc_id: int_relevance}}
# run:   {query_id: {doc_id: float_score}}
evaluator = pytrec_eval.RelevanceEvaluator(qrels, MEASURES)
per_query_scores = evaluator.evaluate(run)
# per_query_scores: {query_id: {measure: float}}
```

`MEASURES` constant:
```python
MEASURES = {
    "ndcg_cut_1", "ndcg_cut_3", "ndcg_cut_5", "ndcg_cut_10",
    "map_cut_10",
    "recall_5", "recall_10",
}
```

## Stdout table format

```
Metric           Score
---------------  -------
ndcg_cut_1       0.3012
ndcg_cut_3       0.3540
ndcg_cut_5       0.3801
ndcg_cut_10      0.4150
map_cut_10       0.3321
recall_5         0.4600
recall_10        0.5900
```

## Dependencies

- `pytrec-eval-terrier>=0.5` — already declared in `pyproject.toml`; no new dep needed
- Phase 3 run complete: `results/<run_id>/raw_results.json` must exist
- Phase 1 download complete: `data/<dataset>/qrels/test.tsv` must exist

## Acceptance criteria

1. `searchlab-eval metrics ir --run-id <run_id>` exits 0 and writes
   `results/<run_id>/ir_scores.json` with non-zero aggregate scores.
2. Every query in `raw_results.json` appears as a key in `per_query` (including
   queries with empty result lists, which score 0).
3. `searchlab-eval metrics ir --run-id notexist` exits non-zero with a clear error
   about missing run directory. No Python traceback visible.
4. `pytest tests/test_ir_metrics.py -m "not integration"` passes offline.
