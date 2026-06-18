import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

_JUDGE_MODEL_ENV = "SEARCHLAB_LLM_JUDGE_MODEL"
_JUDGE_MODEL_DEFAULT = "gpt-4o-mini"

_DEFAULT_SEARCHLAB_URL = os.getenv("SEARCHLAB_URL", "http://localhost:8080")

_SEARCHLAB_URL_OPTION = click.option(
    "--searchlab-url", "-U",
    default=_DEFAULT_SEARCHLAB_URL,
    show_default=True,
    envvar="SEARCHLAB_URL",
    help="SearchLab service base URL",
)

_OPENSEARCH_URL_DEPRECATED = click.option(
    "--opensearch-url", "-u",
    default=None,
    hidden=True,
    help="[Deprecated] Use --searchlab-url instead",
)


@click.group()
def cli() -> None:
    """searchlab-eval — reproducible IR/RAG evaluation against BEIR datasets."""


@cli.command()
@click.option("--dataset", "-d", required=True, help="BEIR dataset name (e.g. scifact, nfcorpus)")
@click.option(
    "--slice", "-s", "slice_n",
    default=100, show_default=True,
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
        click.echo(f"Downloaded {dataset}: {len(corpus)} docs, {original_q} → {final_q} queries")
    else:
        click.echo(f"Downloaded {dataset}: {len(corpus)} docs, {final_q} queries")


@cli.command()
@click.option("--dataset", "-d", required=True, help="BEIR dataset name (e.g. scifact, nfcorpus)")
@_SEARCHLAB_URL_OPTION
@_OPENSEARCH_URL_DEPRECATED
def ingest(dataset: str, searchlab_url: str, opensearch_url: str | None) -> None:
    """Ingest a downloaded BEIR corpus via the searchlab service."""
    from searchlab_eval.ingestor import ingest_corpus

    if opensearch_url:
        click.echo("Warning: --opensearch-url is deprecated; use --searchlab-url instead", err=True)

    index = f"searchlab-{dataset}"
    corpus_path = Path("data") / dataset / "corpus.jsonl"
    if not corpus_path.exists():
        click.echo(f"Error: corpus not found at {corpus_path} — run download first", err=True)
        sys.exit(1)

    try:
        n_ingested = ingest_corpus(corpus_path, searchlab_url, index=index)
    except RuntimeError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Ingested {n_ingested} docs into {index} via {searchlab_url}")


@cli.command()
@click.option("--dataset", "-d", required=True, help="BEIR dataset name (e.g. scifact, nfcorpus)")
@click.option("--top-k", "-k", default=10, show_default=True, help="Number of results per query")
@_SEARCHLAB_URL_OPTION
@_OPENSEARCH_URL_DEPRECATED
@click.option("--run-id", default=None, help="Run identifier (auto-generated if omitted)")
def query(dataset: str, top_k: int, searchlab_url: str, opensearch_url: str | None, run_id: str | None) -> None:
    """Run queries for a downloaded BEIR dataset and write ranked results."""
    from searchlab_eval.querier import load_queries, run_queries

    if opensearch_url:
        click.echo("Warning: --opensearch-url is deprecated; use --searchlab-url instead", err=True)

    queries_path = Path("data") / dataset / "queries.jsonl"
    if not queries_path.exists():
        click.echo(f"Error: queries not found at {queries_path} — run download first", err=True)
        sys.exit(1)

    queries = load_queries(queries_path)

    if run_id is None:
        run_id = f"{dataset}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    results_dir = Path("results") / run_id
    results_dir.mkdir(parents=True, exist_ok=True)

    results = run_queries(queries, searchlab_url, top_k, dataset=dataset)

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
        MEASURES, aggregate, build_pytrec_run, compute_metrics,
        format_table, load_qrels, load_run,
    )

    run_path = Path("results") / run_id / "raw_results.json"
    if not run_path.exists():
        click.echo(f"Error: run not found at {run_path} — run 'searchlab-eval query' first", err=True)
        sys.exit(1)

    _, dataset, results = load_run(run_path)

    qrels_path = Path("data") / dataset / "qrels" / "test.tsv"
    if not qrels_path.exists():
        click.echo(f"Error: qrels not found at {qrels_path} — run 'searchlab-eval download' first", err=True)
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


@cli.command("ragas")
@click.option("--dataset", "-d", required=True, help="BEIR dataset name (e.g. fiqa, nfcorpus)")
@click.option(
    "--slice", "-s", "slice_n",
    default=50, show_default=True,
    help="Number of queries to evaluate (0 = all)",
)
@click.option("--run-id", default=None, help="Run ID directory name (auto-generated if omitted)")
@_SEARCHLAB_URL_OPTION
def ragas_cmd(dataset: str, slice_n: int, run_id: str | None, searchlab_url: str) -> None:
    """Generate RAG answers via POST /rag and score locally with RAGAS."""
    from searchlab_eval.querier import load_queries
    from searchlab_eval.rag_eval import generate, score

    judge_model = os.getenv(_JUDGE_MODEL_ENV, _JUDGE_MODEL_DEFAULT)

    if run_id is None:
        run_id = f"{dataset}-ragas-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    run_dir = Path("results") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    queries_path = Path("data") / dataset / "queries.jsonl"
    if not queries_path.exists():
        click.echo(
            f"Error: queries not found at {queries_path} — run 'searchlab-eval download' first",
            err=True,
        )
        sys.exit(1)

    queries = load_queries(queries_path)
    original_n = len(queries)

    if slice_n > 0 and slice_n < len(queries):
        ids = sorted(queries.keys())[:slice_n]
        queries = {qid: queries[qid] for qid in ids}

    click.echo(f"Dataset:      {dataset}")
    click.echo(f"Queries:      {len(queries)}/{original_n}")
    click.echo(f"Run ID:       {run_id}")
    click.echo(f"Judge model:  {judge_model}  (set {_JUDGE_MODEL_ENV} to override)")
    click.echo(f"Service URL:  {searchlab_url}")
    click.echo()

    # ── Step 1: Generation ───────────────────────────────────────────────────
    click.echo("Step 1/2 — Generating answers via POST /rag …")
    results = generate(
        queries=queries,
        data_dir=Path("data") / dataset,
        dataset=dataset,
        searchlab_url=searchlab_url,
    )

    if not results:
        click.echo("Error: no results generated — check that the service is running", err=True)
        sys.exit(1)

    rag_results_path = run_dir / "rag_results.json"
    rag_results_path.write_text(json.dumps({
        "run_id":       run_id,
        "dataset":      dataset,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "per_query":    results,
    }, indent=2))
    click.echo(f"Written: results/{run_id}/rag_results.json ({len(results)} queries)")
    click.echo()

    # ── Step 2: Scoring ──────────────────────────────────────────────────────
    click.echo(f"Step 2/2 — Scoring with RAGAS (judge: {judge_model}) …")
    try:
        aggregate, per_query, measure_names = score(
            results=results,
            dataset=dataset,
            judge_model=judge_model,
        )
    except Exception as exc:
        click.echo(f"Error: RAGAS scoring failed: {exc}", err=True)
        sys.exit(1)

    rag_scores_path = run_dir / "rag_scores.json"
    rag_scores_path.write_text(json.dumps({
        "run_id":      run_id,
        "dataset":     dataset,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "measures":    measure_names,
        "judge_model": judge_model,
        "aggregate":   aggregate,
        "per_query":   per_query,
    }, indent=2))

    click.echo()
    click.echo(f"{'Metric':<22}  {'Score':>7}")
    click.echo(f"{'-' * 22}  {'-' * 7}")
    for m in measure_names:
        click.echo(f"{m:<22}  {aggregate.get(m, 0.0):>7.4f}")
    click.echo()
    click.echo(f"Scores written to results/{run_id}/rag_scores.json")


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
