import json

import pytest

from searchlab.web import compare


@pytest.fixture(autouse=True)
def _redirect_results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(compare, "_RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(compare, "_DATA_DIR", tmp_path / "data")
    return tmp_path


def _write(tmp_path, run_id, filename, data):
    d = tmp_path / "results" / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(json.dumps(data))


def _write_jsonl(tmp_path, dataset, filename, entries):
    d = tmp_path / "data" / dataset
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text("\n".join(json.dumps(e) for e in entries))


def _write_qrels(tmp_path, dataset, rows):
    d = tmp_path / "data" / dataset / "qrels"
    d.mkdir(parents=True, exist_ok=True)
    lines = ["query-id\tcorpus-id\tscore"] + [f"{qid}\t{doc_id}\t{score}" for qid, doc_id, score in rows]
    (d / "test.tsv").write_text("\n".join(lines))


def _ir_scores(dataset="nfcorpus", per_query=None, measures=None):
    return {
        "dataset": dataset,
        "computed_at": "2026-01-01T00:00:00Z",
        "measures": measures or ["ndcg_cut_10", "recall_10"],
        "aggregate": {},
        "per_query": per_query or {},
    }


def _raw_results(results=None):
    return {"results": results or {}}


def _rag_scores(dataset="nfcorpus", per_query=None, measures=None):
    return {
        "dataset": dataset,
        "computed_at": "2026-01-01T00:00:00Z",
        "measures": measures or ["faithfulness", "answer_relevancy"],
        "aggregate": {},
        "per_query": per_query or {},
    }


def _rag_results(per_query=None):
    return {"per_query": per_query or []}


# ── compare_ir ───────────────────────────────────────────────────────

def test_compare_ir_matched_rows(tmp_path):
    _write(tmp_path, "run-a", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.5, "recall_10": 0.4},
        "Q2": {"ndcg_cut_10": 0.2, "recall_10": 0.1},
    }))
    _write(tmp_path, "run-b", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.8, "recall_10": 0.4},
        "Q2": {"ndcg_cut_10": 0.1, "recall_10": 0.1},
    }))

    result = compare.compare_ir("run-a", "run-b")

    assert result["dataset"] == "nfcorpus"
    assert set(result["measures"]) == {"ndcg_cut_10", "recall_10"}
    assert result["only_in_a"] == []
    assert result["only_in_b"] == []

    rows = {r["query_id"]: r for r in result["rows"]}
    assert rows["Q1"]["a"]["ndcg_cut_10"] == 0.5
    assert rows["Q1"]["b"]["ndcg_cut_10"] == 0.8
    assert rows["Q1"]["delta"]["ndcg_cut_10"] == pytest.approx(0.3)
    assert rows["Q1"]["delta"]["recall_10"] == pytest.approx(0.0)
    assert rows["Q2"]["delta"]["ndcg_cut_10"] == pytest.approx(-0.1)


def test_compare_ir_only_in_a_and_b(tmp_path):
    _write(tmp_path, "run-a", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.5, "recall_10": 0.4},
        "Q_ONLY_A": {"ndcg_cut_10": 0.9, "recall_10": 0.9},
    }))
    _write(tmp_path, "run-b", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.8, "recall_10": 0.4},
        "Q_ONLY_B": {"ndcg_cut_10": 0.3, "recall_10": 0.3},
    }))

    result = compare.compare_ir("run-a", "run-b")

    assert [r["query_id"] for r in result["rows"]] == ["Q1"]
    assert [r["query_id"] for r in result["only_in_a"]] == ["Q_ONLY_A"]
    assert [r["query_id"] for r in result["only_in_b"]] == ["Q_ONLY_B"]
    assert result["only_in_a"][0]["a"]["ndcg_cut_10"] == 0.9


def test_compare_ir_attaches_sources_when_raw_results_present(tmp_path):
    _write(tmp_path, "run-a", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.5, "recall_10": 0.4},
    }))
    _write(tmp_path, "run-a", "raw_results.json", _raw_results({
        "Q1": [{"doc_id": "D1", "score": 1.0, "rank": 1}],
    }))
    _write(tmp_path, "run-b", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.8, "recall_10": 0.4},
    }))
    # run-b has no raw_results.json

    result = compare.compare_ir("run-a", "run-b")

    row = result["rows"][0]
    assert row["sources_a"] == [{"doc_id": "D1", "score": 1.0, "rank": 1}]
    assert row["sources_b"] is None


def test_compare_ir_dataset_mismatch_raises_value_error(tmp_path):
    _write(tmp_path, "run-a", "ir_scores.json", _ir_scores(dataset="nfcorpus"))
    _write(tmp_path, "run-b", "ir_scores.json", _ir_scores(dataset="fiqa"))

    with pytest.raises(ValueError, match="Dataset mismatch"):
        compare.compare_ir("run-a", "run-b")


def test_compare_ir_missing_run_raises_file_not_found(tmp_path):
    _write(tmp_path, "run-a", "ir_scores.json", _ir_scores())

    with pytest.raises(FileNotFoundError):
        compare.compare_ir("run-a", "does-not-exist")


# ── compare_rag ──────────────────────────────────────────────────────

def test_compare_rag_matched_rows_by_position(tmp_path):
    _write(tmp_path, "run-a", "rag_scores.json", _rag_scores(per_query={
        "0": {"faithfulness": 0.5, "answer_relevancy": 0.6},
        "1": {"faithfulness": 0.2, "answer_relevancy": 0.3},
    }))
    _write(tmp_path, "run-a", "rag_results.json", _rag_results([
        {"query_id": "Q1", "question": "q1?", "answer": "a1", "contexts": [], "ground_truth": None},
        {"query_id": "Q2", "question": "q2?", "answer": "a2", "contexts": [], "ground_truth": None},
    ]))
    _write(tmp_path, "run-b", "rag_scores.json", _rag_scores(per_query={
        "0": {"faithfulness": 0.9, "answer_relevancy": 0.6},
        "1": {"faithfulness": 0.1, "answer_relevancy": 0.3},
    }))
    _write(tmp_path, "run-b", "rag_results.json", _rag_results([
        {"query_id": "Q1", "question": "q1?", "answer": "b1", "contexts": [], "ground_truth": None},
        {"query_id": "Q2", "question": "q2?", "answer": "b2", "contexts": [], "ground_truth": None},
    ]))

    result = compare.compare_rag("run-a", "run-b")

    assert result["only_in_a"] == []
    assert result["only_in_b"] == []
    row0 = result["rows"][0]
    assert row0["query_id"] == "Q1"
    assert row0["a"]["faithfulness"] == 0.5
    assert row0["b"]["faithfulness"] == 0.9
    assert row0["delta"]["faithfulness"] == pytest.approx(0.4)
    assert row0["content_a"]["answer"] == "a1"
    assert row0["content_b"]["answer"] == "b1"


def test_compare_rag_different_slice_sizes_surfaces_overflow(tmp_path):
    _write(tmp_path, "run-a", "rag_scores.json", _rag_scores(per_query={
        "0": {"faithfulness": 0.5, "answer_relevancy": 0.6},
    }))
    _write(tmp_path, "run-a", "rag_results.json", _rag_results([
        {"query_id": "Q1", "question": "q1?", "answer": "a1", "contexts": [], "ground_truth": None},
    ]))
    _write(tmp_path, "run-b", "rag_scores.json", _rag_scores(per_query={
        "0": {"faithfulness": 0.9, "answer_relevancy": 0.6},
        "1": {"faithfulness": 0.4, "answer_relevancy": 0.2},
    }))
    _write(tmp_path, "run-b", "rag_results.json", _rag_results([
        {"query_id": "Q1", "question": "q1?", "answer": "b1", "contexts": [], "ground_truth": None},
        {"query_id": "Q2", "question": "q2?", "answer": "b2", "contexts": [], "ground_truth": None},
    ]))

    result = compare.compare_rag("run-a", "run-b")

    assert len(result["rows"]) == 1
    assert result["only_in_a"] == []
    assert len(result["only_in_b"]) == 1
    assert result["only_in_b"][0]["query_id"] == "Q2"
    assert result["only_in_b"][0]["index"] == 1


def test_compare_rag_dataset_mismatch_raises_value_error(tmp_path):
    _write(tmp_path, "run-a", "rag_scores.json", _rag_scores(dataset="nfcorpus"))
    _write(tmp_path, "run-a", "rag_results.json", _rag_results([]))
    _write(tmp_path, "run-b", "rag_scores.json", _rag_scores(dataset="fiqa"))
    _write(tmp_path, "run-b", "rag_results.json", _rag_results([]))

    with pytest.raises(ValueError, match="Dataset mismatch"):
        compare.compare_rag("run-a", "run-b")


def test_compare_rag_missing_run_raises_file_not_found(tmp_path):
    _write(tmp_path, "run-a", "rag_scores.json", _rag_scores())
    _write(tmp_path, "run-a", "rag_results.json", _rag_results([]))

    with pytest.raises(FileNotFoundError):
        compare.compare_rag("run-a", "does-not-exist")


# ── query_text ───────────────────────────────────────────────────────

def test_compare_ir_attaches_query_text_from_queries_jsonl(tmp_path):
    _write(tmp_path, "run-a", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.5, "recall_10": 0.4},
        "Q_ONLY_A": {"ndcg_cut_10": 0.9, "recall_10": 0.9},
    }))
    _write(tmp_path, "run-b", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.8, "recall_10": 0.4},
        "Q_ONLY_B": {"ndcg_cut_10": 0.3, "recall_10": 0.3},
    }))
    _write_jsonl(tmp_path, "nfcorpus", "queries.jsonl", [
        {"_id": "Q1", "text": "What is Q1 about?"},
        {"_id": "Q_ONLY_A", "text": "Only in A question"},
        {"_id": "Q_ONLY_B", "text": "Only in B question"},
    ])

    result = compare.compare_ir("run-a", "run-b")

    rows = {r["query_id"]: r for r in result["rows"]}
    assert rows["Q1"]["query_text"] == "What is Q1 about?"
    assert result["only_in_a"][0]["query_text"] == "Only in A question"
    assert result["only_in_b"][0]["query_text"] == "Only in B question"


def test_compare_ir_query_text_null_when_queries_jsonl_missing(tmp_path):
    _write(tmp_path, "run-a", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.5, "recall_10": 0.4},
    }))
    _write(tmp_path, "run-b", "ir_scores.json", _ir_scores(per_query={
        "Q1": {"ndcg_cut_10": 0.8, "recall_10": 0.4},
    }))

    result = compare.compare_ir("run-a", "run-b")

    assert result["rows"][0]["query_text"] is None


def test_compare_rag_attaches_query_text_and_flags_mismatch(tmp_path):
    _write(tmp_path, "run-a", "rag_scores.json", _rag_scores(per_query={
        "0": {"faithfulness": 0.5, "answer_relevancy": 0.6},
        "1": {"faithfulness": 0.2, "answer_relevancy": 0.3},
    }))
    _write(tmp_path, "run-a", "rag_results.json", _rag_results([
        {"query_id": "Q1", "question": "same question?", "answer": "a1", "contexts": [], "ground_truth": None},
        {"query_id": "Q2", "question": "run-a question?", "answer": "a2", "contexts": [], "ground_truth": None},
    ]))
    _write(tmp_path, "run-b", "rag_scores.json", _rag_scores(per_query={
        "0": {"faithfulness": 0.9, "answer_relevancy": 0.6},
        "1": {"faithfulness": 0.1, "answer_relevancy": 0.3},
    }))
    _write(tmp_path, "run-b", "rag_results.json", _rag_results([
        {"query_id": "Q1", "question": "same question?", "answer": "b1", "contexts": [], "ground_truth": None},
        {"query_id": "Q2", "question": "run-b question?", "answer": "b2", "contexts": [], "ground_truth": None},
    ]))

    result = compare.compare_rag("run-a", "run-b")

    assert result["rows"][0]["query_text"] == "same question?"
    assert "query_text_mismatch" not in result["rows"][0]
    assert result["rows"][1]["query_text"] == "run-a question?"
    assert result["rows"][1]["query_text_mismatch"] is True


# ── load_document ────────────────────────────────────────────────────

def test_load_document_found(tmp_path):
    _write_jsonl(tmp_path, "nfcorpus", "corpus.jsonl", [
        {"_id": "MED-1", "title": "Doc One", "text": "Some text about doc one."},
        {"_id": "MED-2", "title": "Doc Two", "text": "Some text about doc two."},
    ])

    doc = compare.load_document("nfcorpus", "MED-2")

    assert doc == {"doc_id": "MED-2", "title": "Doc Two", "text": "Some text about doc two."}


def test_load_document_missing_doc_id_raises(tmp_path):
    _write_jsonl(tmp_path, "nfcorpus", "corpus.jsonl", [
        {"_id": "MED-1", "title": "Doc One", "text": "Some text."},
    ])

    with pytest.raises(FileNotFoundError, match="MED-999"):
        compare.load_document("nfcorpus", "MED-999")


def test_load_document_missing_dataset_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="nfcorpus"):
        compare.load_document("nfcorpus", "MED-1")


# ── load_qrels ───────────────────────────────────────────────────────

def test_load_qrels_found(tmp_path):
    _write_qrels(tmp_path, "nfcorpus", [
        ("PLAIN-2", "MED-14", 2),
        ("PLAIN-2", "MED-15", 1),
        ("PLAIN-3", "MED-16", 1),
    ])

    judgements = compare.load_qrels("nfcorpus", "PLAIN-2")

    assert judgements == [{"doc_id": "MED-14", "score": 2}, {"doc_id": "MED-15", "score": 1}]


def test_load_qrels_query_with_no_judgements_returns_empty_list(tmp_path):
    _write_qrels(tmp_path, "nfcorpus", [("PLAIN-2", "MED-14", 2)])

    assert compare.load_qrels("nfcorpus", "PLAIN-999") == []


def test_load_qrels_missing_dataset_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="nfcorpus"):
        compare.load_qrels("nfcorpus", "PLAIN-2")


# ── ground_truth (RAG) ──────────────────────────────────────────────

def test_compare_rag_attaches_ground_truth_and_flags_mismatch(tmp_path):
    _write(tmp_path, "run-a", "rag_scores.json", _rag_scores(per_query={
        "0": {"faithfulness": 0.5, "answer_relevancy": 0.6},
        "1": {"faithfulness": 0.2, "answer_relevancy": 0.3},
    }))
    _write(tmp_path, "run-a", "rag_results.json", _rag_results([
        {"query_id": "Q1", "question": "q1?", "answer": "a1", "contexts": [], "ground_truth": "same truth"},
        {"query_id": "Q2", "question": "q2?", "answer": "a2", "contexts": [], "ground_truth": "truth from a"},
    ]))
    _write(tmp_path, "run-b", "rag_scores.json", _rag_scores(per_query={
        "0": {"faithfulness": 0.9, "answer_relevancy": 0.6},
        "1": {"faithfulness": 0.1, "answer_relevancy": 0.3},
    }))
    _write(tmp_path, "run-b", "rag_results.json", _rag_results([
        {"query_id": "Q1", "question": "q1?", "answer": "b1", "contexts": [], "ground_truth": "same truth"},
        {"query_id": "Q2", "question": "q2?", "answer": "b2", "contexts": [], "ground_truth": "truth from b"},
    ]))

    result = compare.compare_rag("run-a", "run-b")

    assert result["rows"][0]["ground_truth"] == "same truth"
    assert "ground_truth_mismatch" not in result["rows"][0]
    assert result["rows"][1]["ground_truth"] == "truth from a"
    assert result["rows"][1]["ground_truth_mismatch"] is True
