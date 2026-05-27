import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from searchlab_eval.querier import _parse_hits, load_queries, run_queries, run_query

NORMAL_OUTPUT = (
    "Rank  Score    Source                          Page  Snippet\n"
    "----------------------------------------------------------------------------------------------------\n"
    "1     0.6442   doc-abc                         0     Some snippet text here\n"
    "2     0.4716   doc-xyz                         0     Another snippet\n"
)


def test_parse_hits_normal():
    hits = _parse_hits(NORMAL_OUTPUT)
    assert len(hits) == 2
    assert hits[0] == {"doc_id": "doc-abc", "score": 0.6442, "rank": 1}
    assert hits[1] == {"doc_id": "doc-xyz", "score": 0.4716, "rank": 2}


def test_parse_hits_no_results():
    hits = _parse_hits("No results found for: some query")
    assert hits == []


def test_parse_hits_empty_output():
    assert _parse_hits("") == []
    header_only = (
        "Rank  Score    Source                          Page  Snippet\n"
        "----------------------------------------------------------------------------------------------------\n"
    )
    assert _parse_hits(header_only) == []


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
    assert result == {"q1": "What is oxygen?", "q2": "Hypoxia treatment", "q3": "Cancer immunotherapy"}


def test_run_query_nonzero_exit():
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "connection refused"

    with patch("subprocess.run", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="exited 1"):
            run_query("test query", "http://localhost:9200", 10)


def test_run_queries_continues_on_error():
    queries = {"q1": "first query", "q2": "second query"}

    def fake_run_query(text, url, top_k):
        if text == "first query":
            raise RuntimeError("connection failed")
        return [{"doc_id": "doc-1", "score": 0.9, "rank": 1}]

    with patch("searchlab_eval.querier.run_query", side_effect=fake_run_query):
        results = run_queries(queries, "http://localhost:9200", 10)

    assert "q1" in results
    assert "q2" in results
    assert results["q1"] == []
    assert results["q2"] == [{"doc_id": "doc-1", "score": 0.9, "rank": 1}]


@pytest.mark.integration
def test_query_nfcorpus(tmp_path):
    queries_path = Path("data/nfcorpus/queries.jsonl")
    if not queries_path.exists():
        pytest.skip("data/nfcorpus/queries.jsonl not present")

    all_queries = load_queries(queries_path)
    slice_queries = dict(list(all_queries.items())[:3])

    results = run_queries(slice_queries, "http://localhost:9200", top_k=5)

    assert set(results.keys()) == set(slice_queries.keys())
    assert any(len(v) > 0 for v in results.values())
