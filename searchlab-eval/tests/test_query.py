import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from searchlab_eval.querier import load_queries, run_queries, run_query


def _make_hits_response(hits: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"hits": hits, "index": "searchlab-test"}
    return resp


# ── run_query ────────────────────────────────────────────────────────

def test_run_query_maps_doc_id():
    hits = [
        {"rank": 1, "score": 0.9, "doc_id": "MED-10", "filename": "MED-10", "page": 0, "snippet": "..."},
        {"rank": 2, "score": 0.5, "doc_id": "MED-20", "filename": "MED-20", "page": 0, "snippet": "..."},
    ]
    with patch("requests.post", return_value=_make_hits_response(hits)):
        result = run_query("test query", "http://localhost:8080", 10, "nfcorpus")

    assert result == [
        {"doc_id": "MED-10", "score": 0.9, "rank": 1},
        {"doc_id": "MED-20", "score": 0.5, "rank": 2},
    ]


def test_run_query_service_unreachable():
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
        with pytest.raises(RuntimeError, match="unreachable"):
            run_query("test query", "http://localhost:8080", 10, "nfcorpus")


def test_run_query_error_in_response():
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"error": "index not found"}
    with patch("requests.post", return_value=resp):
        with pytest.raises(RuntimeError, match="index not found"):
            run_query("test query", "http://localhost:8080", 10, "nfcorpus")


def test_run_query_empty_results():
    with patch("requests.post", return_value=_make_hits_response([])):
        result = run_query("test query", "http://localhost:8080", 10, "nfcorpus")
    assert result == []


# ── load_queries ─────────────────────────────────────────────────────

def test_load_queries_missing_file():
    with pytest.raises(FileNotFoundError):
        load_queries(Path("nonexistent.jsonl"))


def test_load_queries_content(tmp_path):
    queries_file = tmp_path / "queries.jsonl"
    rows = [
        {"_id": "q1", "text": "What is oxygen?"},
        {"_id": "q2", "text": "Hypoxia treatment"},
        {"_id": "q3", "text": "Cancer immunotherapy"},
    ]
    queries_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    result = load_queries(queries_file)
    assert result == {
        "q1": "What is oxygen?",
        "q2": "Hypoxia treatment",
        "q3": "Cancer immunotherapy",
    }


# ── run_queries ──────────────────────────────────────────────────────

def test_run_queries_continues_on_error():
    queries = {"q1": "first query", "q2": "second query"}

    def fake_run_query(text, url, top_k, dataset):
        if text == "first query":
            raise RuntimeError("connection failed")
        return [{"doc_id": "doc-1", "score": 0.9, "rank": 1}]

    with patch("searchlab_eval.querier.run_query", side_effect=fake_run_query):
        results = run_queries(queries, "http://localhost:8080", 10, dataset="nfcorpus")

    assert results["q1"] == []
    assert results["q2"] == [{"doc_id": "doc-1", "score": 0.9, "rank": 1}]


@pytest.mark.integration
def test_query_nfcorpus(tmp_path):
    queries_path = Path("data/nfcorpus/queries.jsonl")
    if not queries_path.exists():
        pytest.skip("data/nfcorpus/queries.jsonl not present")

    all_queries = load_queries(queries_path)
    slice_queries = dict(list(all_queries.items())[:3])

    results = run_queries(slice_queries, "http://localhost:8080", top_k=5, dataset="nfcorpus")
    assert set(results.keys()) == set(slice_queries.keys())
    assert any(len(v) > 0 for v in results.values())
