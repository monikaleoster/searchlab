import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from searchlab_eval.ingestor import ingest_corpus


def _make_response(indexed: int = 3) -> MagicMock:
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"indexed": indexed}
    return resp


def test_ingest_corpus_single_batch(tmp_path):
    corpus_file = tmp_path / "corpus.jsonl"
    docs = [{"_id": str(i), "title": f"T{i}", "text": f"B{i}"} for i in range(3)]
    corpus_file.write_text("\n".join(json.dumps(d) for d in docs) + "\n")

    with patch("requests.post", return_value=_make_response(3)) as mock_post:
        total = ingest_corpus(corpus_file, "http://localhost:8080", index="searchlab-test")

    assert total == 3
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["params"] == {"index": "searchlab-test"}
    assert len(call_kwargs.kwargs["json"]) == 3


def test_batch_splitting(tmp_path):
    corpus_file = tmp_path / "corpus.jsonl"
    with corpus_file.open("w") as fh:
        for i in range(1200):
            fh.write(json.dumps({"_id": str(i), "title": f"T{i}", "text": f"B{i}"}) + "\n")

    call_counts = []

    def fake_post(url, params, json, timeout):
        call_counts.append(len(json))
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {"indexed": len(json)}
        return resp

    with patch("requests.post", side_effect=fake_post):
        total = ingest_corpus(corpus_file, "http://localhost:8080", index="searchlab-test")

    assert len(call_counts) == 3  # ceil(1200 / 500)
    assert total == 1200


def test_missing_corpus_raises():
    with pytest.raises(FileNotFoundError):
        ingest_corpus(Path("nonexistent.jsonl"), "http://localhost:8080", index="x")


def test_service_unreachable(tmp_path):
    corpus_file = tmp_path / "corpus.jsonl"
    corpus_file.write_text(json.dumps({"_id": "1", "title": "T", "text": "B"}) + "\n")

    with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
        with pytest.raises(RuntimeError, match="unreachable"):
            ingest_corpus(corpus_file, "http://localhost:8080", index="x")


def test_error_in_response_raises(tmp_path):
    corpus_file = tmp_path / "corpus.jsonl"
    corpus_file.write_text(json.dumps({"_id": "1", "title": "T", "text": "B"}) + "\n")

    bad_resp = MagicMock()
    bad_resp.ok = True
    bad_resp.json.return_value = {"error": "index mapping error"}

    with patch("requests.post", return_value=bad_resp):
        with pytest.raises(RuntimeError, match="index mapping error"):
            ingest_corpus(corpus_file, "http://localhost:8080", index="x")


@pytest.mark.integration
def test_ingest_nfcorpus():
    corpus_path = Path("data/nfcorpus/corpus.jsonl")
    if not corpus_path.exists():
        pytest.skip("data/nfcorpus/corpus.jsonl not present — run download first")
    n_ingested = ingest_corpus(corpus_path, "http://localhost:8080", index="searchlab-nfcorpus")
    assert n_ingested > 0
