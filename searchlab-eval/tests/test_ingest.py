import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from searchlab_eval.ingestor import (
    _build_bulk_body,
    _post_bulk,
    get_doc_count,
    ingest_corpus,
)


# ── unit tests (no network) ──────────────────────────────────────────────────

def test_bulk_body_format():
    docs = [
        {"_id": "doc1", "title": "Hello", "text": "World"},
        {"_id": "doc2", "title": "Foo", "text": "Bar"},
    ]
    body = _build_bulk_body(docs, "2026-01-01T00:00:00+00:00")
    lines = [l for l in body.split("\n") if l]
    assert len(lines) == 4  # 2 action lines + 2 doc lines

    action = json.loads(lines[0])
    assert action == {"index": {"_index": "searchlab-v0", "_id": "doc1"}}

    doc = json.loads(lines[1])
    assert doc["chunk_id"] == "doc1"
    assert doc["chunk_text"] == "Hello World"
    assert doc["source_filename"] == "doc1"
    assert doc["page_number"] == 0
    assert doc["chunk_position"] == 0

    action2 = json.loads(lines[2])
    assert action2["index"]["_id"] == "doc2"

    doc2 = json.loads(lines[3])
    assert doc2["chunk_text"] == "Foo Bar"


def test_batch_splitting(tmp_path):
    corpus_file = tmp_path / "corpus.jsonl"
    with corpus_file.open("w") as fh:
        for i in range(1200):
            fh.write(json.dumps({"_id": str(i), "title": f"T{i}", "text": f"B{i}"}) + "\n")

    call_args = []

    def fake_post_bulk(url, body):
        call_args.append(body)

    with patch("searchlab_eval.ingestor._post_bulk", side_effect=fake_post_bulk):
        total = ingest_corpus(corpus_file, "http://localhost:9200")

    assert len(call_args) == 3  # ceil(1200 / 500)
    assert total == 1200


def test_missing_corpus_raises():
    with pytest.raises(FileNotFoundError):
        ingest_corpus(Path("nonexistent.jsonl"), "http://localhost:9200")


def test_opensearch_unreachable(tmp_path):
    corpus_file = tmp_path / "corpus.jsonl"
    corpus_file.write_text(
        json.dumps({"_id": "1", "title": "T", "text": "B"}) + "\n"
    )

    with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
        with pytest.raises(RuntimeError, match="unreachable"):
            ingest_corpus(corpus_file, "http://localhost:9200")


def test_bulk_errors_raise(tmp_path):
    corpus_file = tmp_path / "corpus.jsonl"
    corpus_file.write_text(
        json.dumps({"_id": "1", "title": "T", "text": "B"}) + "\n"
    )

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "errors": True,
        "items": [{"index": {"error": {"reason": "mapping error"}}}],
    }

    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="mapping error"):
            ingest_corpus(corpus_file, "http://localhost:9200")


# ── integration test (requires running OpenSearch) ────────────────────────────

@pytest.mark.integration
def test_ingest_nfcorpus():
    corpus_path = Path("data/nfcorpus/corpus.jsonl")
    if not corpus_path.exists():
        pytest.skip("data/nfcorpus/corpus.jsonl not present — run download first")

    url = "http://localhost:9200"
    n_ingested = ingest_corpus(corpus_path, url)
    assert n_ingested > 0

    n_count = get_doc_count(url)
    assert n_count >= n_ingested
