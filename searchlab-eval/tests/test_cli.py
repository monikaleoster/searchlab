import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from searchlab_eval.cli import cli


def _write_corpus(dataset: str):
    corpus_dir = Path("data") / dataset
    corpus_dir.mkdir(parents=True, exist_ok=True)
    (corpus_dir / "corpus.jsonl").write_text(json.dumps({"_id": "1", "title": "T", "text": "B"}) + "\n")


def _write_queries(dataset: str):
    queries_dir = Path("data") / dataset
    queries_dir.mkdir(parents=True, exist_ok=True)
    (queries_dir / "queries.jsonl").write_text(json.dumps({"_id": "q1", "text": "hello"}) + "\n")


# ── ingest --index override ──────────────────────────────────────────

def test_ingest_without_index_targets_dataset_derived_index():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_corpus("nfcorpus")
        with patch("searchlab_eval.ingestor.ingest_corpus", return_value=1) as mock_ingest:
            result = runner.invoke(cli, ["ingest", "--dataset", "nfcorpus"])

    assert result.exit_code == 0, result.output
    assert mock_ingest.call_args.kwargs["index"] == "searchlab-nfcorpus"
    assert "searchlab-nfcorpus" in result.output


def test_ingest_with_index_overrides_dataset_derived_index():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_corpus("nfcorpus")
        with patch("searchlab_eval.ingestor.ingest_corpus", return_value=1) as mock_ingest:
            result = runner.invoke(cli, ["ingest", "--dataset", "nfcorpus", "--index", "searchlab-custom"])

    assert result.exit_code == 0, result.output
    assert mock_ingest.call_args.kwargs["index"] == "searchlab-custom"
    assert "searchlab-custom" in result.output


# ── query --index override ───────────────────────────────────────────

def test_query_without_index_passes_none_through():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_queries("nfcorpus")
        with patch("searchlab_eval.querier.run_queries", return_value={"q1": []}) as mock_run_queries:
            result = runner.invoke(cli, ["query", "--dataset", "nfcorpus", "--run-id", "run1"])

    assert result.exit_code == 0, result.output
    assert mock_run_queries.call_args.kwargs["index"] is None


def test_query_with_index_passes_override_through():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_queries("nfcorpus")
        with patch("searchlab_eval.querier.run_queries", return_value={"q1": []}) as mock_run_queries:
            result = runner.invoke(
                cli, ["query", "--dataset", "nfcorpus", "--run-id", "run1", "--index", "searchlab-custom"]
            )

    assert result.exit_code == 0, result.output
    assert mock_run_queries.call_args.kwargs["index"] == "searchlab-custom"