import sys
from pathlib import Path

import click

from . import config
from .opensearch.client import create_client
from .opensearch.index_bootstrap import ensure_index_exists
from .ingest.pdf_parser import parse_pdf
from .ingest.chunker import chunk
from .ingest.indexer import index_chunks
from .search.bm25_searcher import search as bm25_search
from .rag import run_rag


@click.group()
def cli():
    """SearchLab — BM25 retrieval and RAG over indexed documents."""


@cli.command()
@click.argument("pdf_path")
def ingest(pdf_path: str):
    """Parse a PDF and index its chunks into OpenSearch."""
    p = Path(pdf_path)
    if not p.exists():
        click.echo(f"Error: file not found: {pdf_path}", err=True)
        sys.exit(1)
    if not pdf_path.lower().endswith(".pdf"):
        click.echo("Error: file must be a .pdf", err=True)
        sys.exit(1)

    client = create_client()
    index = config.index_name()
    ensure_index_exists(client, index)

    pages = parse_pdf(p)
    chunks = chunk(pages)
    n = index_chunks(client, chunks, p.name, index)
    click.echo(f"Indexed {n} chunks from {p.name} into {index}")


@cli.command()
@click.argument("question")
@click.option("--top-k", default=10, show_default=True, help="Number of results")
@click.option("--index", default=None, help="OpenSearch index (default: $SEARCHLAB_INDEX)")
def query(question: str, top_k: int, index: str | None):
    """Run a BM25 search and print ranked results."""
    client = create_client()
    idx = index or config.index_name()
    hits = bm25_search(client, question, top_k, idx)
    if not hits:
        click.echo("No results found.")
        return
    click.echo(f"{'Rank':<5}  {'Score':<8}  {'Source':<32}  {'Page':<5}  Snippet")
    click.echo("-" * 100)
    for h in hits:
        click.echo(f"{h.rank:<5}  {h.score:<8.4f}  {h.source_filename:<32}  {h.page_number:<5}  {h.snippet[:50]}")


@cli.command()
@click.argument("question")
@click.option("--top-k", default=5, show_default=True, help="Number of passages to retrieve")
@click.option("--model", default=None, help="LLM model (default: $SEARCHLAB_LLM_MODEL or gpt-4o-mini)")
@click.option("--index", default=None, help="OpenSearch index (default: $SEARCHLAB_INDEX)")
def rag(question: str, top_k: int, model: str | None, index: str | None):
    """Retrieve passages via BM25 and generate an answer with an LLM."""
    client = create_client()
    idx = index or config.index_name()
    result = run_rag(question=question, top_k=top_k, model=model, client=client, index=idx)
    if result.error:
        click.echo(f"Error: {result.error}", err=True)
        sys.exit(1)
    click.echo("Answer:")
    click.echo(result.answer)
    if result.sources:
        click.echo()
        click.echo("Sources:")
        for h in result.sources:
            click.echo(f"  [{h.rank}] {h.source_filename}  (score: {h.score:.3f})")


@cli.command()
@click.option("--port", default=8080, show_default=True, help="Port to listen on")
@click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind to")
def serve(port: int, host: str):
    """Launch the SearchLab FastAPI server."""
    import uvicorn
    click.echo(f"SearchLab UI → http://localhost:{port}")
    click.echo("Press Ctrl+C to stop.")
    uvicorn.run("searchlab.main:app", host=host, port=port, reload=False)
