"""Tests for Phase 1 — dataset download and query slicing."""
import pytest

from searchlab_eval.slicer import slice_queries


# ── slicer unit tests (no network) ───────────────────────────────────────────

def _make_queries(n: int) -> dict:
    return {str(i): f"query text {i}" for i in range(n)}


def _make_qrels(queries: dict) -> dict:
    return {qid: {f"doc_{qid}": 1} for qid in queries}


def test_slice_size():
    q = _make_queries(20)
    r = _make_qrels(q)
    sq, sr = slice_queries(q, r, 10)
    assert len(sq) == 10
    assert len(sr) == 10


def test_slice_determinism():
    q = _make_queries(20)
    r = _make_qrels(q)
    sq1, _ = slice_queries(q, r, 10)
    sq2, _ = slice_queries(q, r, 10)
    assert list(sq1.keys()) == list(sq2.keys())


def test_slice_zero_keeps_all():
    q = _make_queries(20)
    r = _make_qrels(q)
    sq, sr = slice_queries(q, r, 0)
    assert len(sq) == 20


def test_slice_n_gte_total_keeps_all():
    q = _make_queries(5)
    r = _make_qrels(q)
    sq, sr = slice_queries(q, r, 100)
    assert len(sq) == 5


def test_slice_ids_are_sorted_prefix():
    q = _make_queries(20)
    r = _make_qrels(q)
    sq, _ = slice_queries(q, r, 5)
    expected_ids = sorted(q.keys())[:5]
    assert list(sq.keys()) == expected_ids


# ── integration test (requires network) ──────────────────────────────────────

@pytest.mark.integration
def test_download_nfcorpus(tmp_path):
    from searchlab_eval.downloader import download_dataset

    data_dir = tmp_path / "nfcorpus"
    corpus, queries, qrels = download_dataset("nfcorpus", data_dir)

    assert len(corpus) > 0, "corpus is empty"
    assert len(queries) > 0, "queries is empty"
    assert len(qrels) > 0, "qrels is empty"

    assert (data_dir / "corpus.jsonl").exists()
    assert (data_dir / "queries.jsonl").exists()
    assert (data_dir / "qrels" / "test.tsv").exists()
