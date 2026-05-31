import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import click


@click.group()
def cli() -> None:
    """searchlab-eval — reproducible IR/RAG evaluation against BEIR datasets."""


@cli.command()
@click.option("--dataset", "-d", required=True, help="BEIR dataset name (e.g. scifact, nfcorpus)")
@click.option(
    "--slice",
    "-s",
    "slice_n",
    default=100,
    show_default=True,
    help="Queries to keep after deterministic slice; 0 keeps all",
)
def download(dataset: str, slice_n: int) -> None:
    """Download a BEIR dataset to data/<dataset>/."""
    from searchlab_eval.downloader import download_dataset
    from searchlab_eval.slicer import slice_queries

    data_dir = Path("data") / dataset

    click.echo(f"Downloading {dataset}…")
    try:
        corpus, queries, qrels = download_dataset(dataset, data_dir)
    except RuntimeError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    original_q = len(queries)

    if slice_n > 0:
        queries, qrels = slice_queries(queries, qrels, slice_n)

    final_q = len(queries)

    _write_queries(data_dir, queries)
    _write_qrels(data_dir, qrels)

    if slice_n > 0 and final_q < original_q:
        click.echo(
            f"Downloaded {dataset}: {len(corpus)} docs, {original_q} → {final_q} queries"
        )
    else:
        click.echo(f"Downloaded {dataset}: {len(corpus)} docs, {final_q} queries")


@cli.command()
@click.option("--dataset", "-d", required=True, help="BEIR dataset name (e.g. scifact, nfcorpus)")
@click.option(
    "--opensearch-url",
    "-u",
    default="http://localhost:9200",
    show_default=True,
    envvar="OPENSEARCH_URL",
    help="OpenSearch base URL",
)
def ingest(dataset: str, opensearch_url: str) -> None:
    """Ingest a downloaded BEIR corpus into OpenSearch."""
    from searchlab_eval.ingestor import get_doc_count, ingest_corpus

    corpus_path = Path("data") / dataset / "corpus.jsonl"
    if not corpus_path.exists():
        click.echo(
            f"Error: corpus not found at {corpus_path} — run download first", err=True
        )
        sys.exit(1)

    try:
        n_ingested = ingest_corpus(corpus_path, opensearch_url)
    except RuntimeError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    try:
        n_count = get_doc_count(opensearch_url)
    except RuntimeError as exc:
        click.echo(f"Warning: could not verify doc count: {exc}", err=True)
        n_count = "?"

    click.echo(f"Ingested {n_ingested} docs into searchlab-v0 (index total: {n_count})")


@cli.command()
@click.option("--dataset", "-d", required=True, help="BEIR dataset name (e.g. scifact, nfcorpus)")
@click.option("--top-k", "-k", default=10, show_default=True, help="Number of results per query")
@click.option(
    "--opensearch-url",
    "-u",
    default="http://localhost:9200",
    show_default=True,
    envvar="OPENSEARCH_URL",
    help="OpenSearch base URL",
)
@click.option("--run-id", default=None, help="Run identifier (auto-generated if omitted)")
def query(dataset: str, top_k: int, opensearch_url: str, run_id: str | None) -> None:
    """Run queries for a downloaded BEIR dataset and write ranked results."""
    from searchlab_eval.querier import load_queries, run_queries

    if shutil.which("searchlab") is None:
        click.echo(
            "Error: 'searchlab' not found on PATH — build the JAR and ensure ./searchlab is executable",
            err=True,
        )
        sys.exit(1)

    queries_path = Path("data") / dataset / "queries.jsonl"
    if not queries_path.exists():
        click.echo(
            f"Error: queries not found at {queries_path} — run download first",
            err=True,
        )
        sys.exit(1)

    queries = load_queries(queries_path)

    if run_id is None:
        run_id = f"{dataset}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    results_dir = Path("results") / run_id
    results_dir.mkdir(parents=True, exist_ok=True)

    results = run_queries(queries, opensearch_url, top_k)

    payload = {
        "run_id": run_id,
        "dataset": dataset,
        "top_k": top_k,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    out_path = results_dir / "raw_results.json"
    out_path.write_text(json.dumps(payload, indent=2))

    click.echo(f"Queried {len(queries)} queries → results/{run_id}/raw_results.json")


@cli.group()
def metrics() -> None:
    """Compute evaluation metrics for a completed run."""


@metrics.command("ir")
@click.option("--run-id", "-r", required=True, help="Run identifier (directory name under results/)")
def metrics_ir(run_id: str) -> None:
    """Compute IR metrics (nDCG, MAP, Recall) for a completed query run."""
    from searchlab_eval.metrics.ir import (
        MEASURES,
        aggregate,
        build_pytrec_run,
        compute_metrics,
        format_table,
        load_qrels,
        load_run,
    )

    run_path = Path("results") / run_id / "raw_results.json"
    if not run_path.exists():
        click.echo(
            f"Error: run not found at {run_path} — run 'searchlab-eval query' first",
            err=True,
        )
        sys.exit(1)

    _, dataset, results = load_run(run_path)

    qrels_path = Path("data") / dataset / "qrels" / "test.tsv"
    if not qrels_path.exists():
        click.echo(
            f"Error: qrels not found at {qrels_path} — run 'searchlab-eval download' first",
            err=True,
        )
        sys.exit(1)

    qrels = load_qrels(qrels_path)
    pytrec_run = build_pytrec_run(results)
    per_query_scores = compute_metrics(pytrec_run, qrels)

    for qid in results:
        if qid not in per_query_scores:
            per_query_scores[qid] = {m: 0.0 for m in MEASURES}

    aggregated = aggregate(per_query_scores)

    payload = {
        "run_id": run_id,
        "dataset": dataset,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "measures": sorted(MEASURES),
        "aggregate": aggregated,
        "per_query": per_query_scores,
    }

    out_path = Path("results") / run_id / "ir_scores.json"
    out_path.write_text(json.dumps(payload, indent=2))

    click.echo(format_table(aggregated))
    click.echo(f"Metrics written to results/{run_id}/ir_scores.json")


# ── helpers ──────────────────────────────────────────────────────────────────

def _write_queries(data_dir: Path, queries: dict) -> None:
    with open(data_dir / "queries.jsonl", "w") as fh:
        for qid, text in queries.items():
            fh.write(json.dumps({"_id": qid, "text": text}) + "\n")


def _write_qrels(data_dir: Path, qrels: dict) -> None:
    qrels_dir = data_dir / "qrels"
    qrels_dir.mkdir(exist_ok=True)
    with open(qrels_dir / "test.tsv", "w") as fh:
        fh.write("query-id\tcorpus-id\tscore\n")
        for qid, docs in qrels.items():
            for doc_id, score in docs.items():
                fh.write(f"{qid}\t{doc_id}\t{score}\n")
