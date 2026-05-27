import json
import sys
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
