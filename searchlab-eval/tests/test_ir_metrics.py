import json
from pathlib import Path

import pytest

from searchlab_eval.metrics.ir import (
    MEASURES,
    aggregate,
    build_pytrec_run,
    compute_metrics,
    format_table,
    load_qrels,
    load_run,
)


def test_load_run_missing_file():
    with pytest.raises(FileNotFoundError):
        load_run(Path("nonexistent.json"))


def test_load_run_content(tmp_path):
    run_file = tmp_path / "raw_results.json"
    payload = {
        "run_id": "nfcorpus-20260526T000000Z",
        "dataset": "nfcorpus",
        "top_k": 10,
        "created_at": "2026-05-26T00:00:00+00:00",
        "results": {"q1": [{"doc_id": "d1", "score": 0.9, "rank": 1}]},
    }
    run_file.write_text(json.dumps(payload))

    run_id, dataset, results = load_run(run_file)

    assert run_id == "nfcorpus-20260526T000000Z"
    assert dataset == "nfcorpus"
    assert results == {"q1": [{"doc_id": "d1", "score": 0.9, "rank": 1}]}


def test_load_qrels_missing_file():
    with pytest.raises(FileNotFoundError):
        load_qrels(Path("nonexistent.tsv"))


def test_load_qrels_content(tmp_path):
    qrels_file = tmp_path / "test.tsv"
    qrels_file.write_text(
        "query-id\tcorpus-id\tscore\n"
        "q1\td1\t1\n"
        "q1\td2\t2\n"
        "q2\td3\t0\n"
    )

    result = load_qrels(qrels_file)

    assert result == {"q1": {"d1": 1, "d2": 2}, "q2": {"d3": 0}}
    assert isinstance(result["q1"]["d1"], int)
    assert isinstance(result["q2"]["d3"], int)


def test_build_pytrec_run():
    results = {
        "q1": [{"doc_id": "d1", "score": 0.9, "rank": 1}, {"doc_id": "d2", "score": 0.5, "rank": 2}],
        "q2": [],
    }
    run = build_pytrec_run(results)

    assert run["q1"] == {"d1": 0.9, "d2": 0.5}
    assert run["q2"] == {}


def test_aggregate_correct_mean():
    per_query = {
        "q1": {m: 0.0 for m in MEASURES} | {"ndcg_cut_10": 0.6},
        "q2": {m: 0.0 for m in MEASURES} | {"ndcg_cut_10": 0.4},
    }
    result = aggregate(per_query)

    assert abs(result["ndcg_cut_10"] - 0.5) < 1e-4


def test_format_table_contains_all_measures():
    agg = {m: 0.0 for m in MEASURES}
    table = format_table(agg)

    for measure in MEASURES:
        assert measure in table


@pytest.mark.integration
def test_metrics_ir_nfcorpus():
    run_files = sorted(Path("results").glob("nfcorpus-*/raw_results.json"))
    if not run_files:
        pytest.skip("No nfcorpus-* query run found in results/")

    run_path = run_files[-1]
    qrels_path = Path("data/nfcorpus/qrels/test.tsv")
    if not qrels_path.exists():
        pytest.skip("data/nfcorpus/qrels/test.tsv not present")

    _, _, results = load_run(run_path)
    qrels = load_qrels(qrels_path)
    pytrec_run = build_pytrec_run(results)
    per_query = compute_metrics(pytrec_run, qrels)
    agg = aggregate(per_query)

    assert agg["ndcg_cut_10"] > 0
    assert set(agg.keys()) == set(MEASURES)
