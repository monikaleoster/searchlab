import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Form, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from .. import config
from ..ingest.pdf_parser import parse_pdf
from ..ingest.chunker import chunk
from ..ingest.indexer import index_chunks, index_corpus_docs
from ..opensearch.client import create_client
from ..opensearch.index_bootstrap import ensure_index_exists
from ..search.bm25_searcher import search as bm25_search
from ..rag import run_rag
from .html import render as render_html

router = APIRouter()

DATASET_INDEX = {
    "nfcorpus": "searchlab-nfcorpus",
    "fiqa": "searchlab-fiqa",
}

# Paths are resolved relative to this file: service/searchlab/web/routes.py
# → service/searchlab/web/ → service/searchlab/ → service/ → repo root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_EVAL_DIR = _REPO_ROOT / "searchlab-eval"
_RESULTS_DIR = _EVAL_DIR / "results"


def _resolve_index(dataset: str, default_index: str | None = None) -> str:
    if dataset == "default":
        return default_index or config.index_name()
    return DATASET_INDEX.get(dataset, config.index_name())


# ── HTML UI ───────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def root():
    has_key = bool(config.openai_api_key())
    return render_html(has_key)


# ── RAG ──────────────────────────────────────────────────────────────

@router.post("/rag")
async def rag_endpoint(
    question: str = Form(""),
    topK: int = Form(5),
    model: str = Form(""),
    dataset: str = Form("default"),
):
    index = _resolve_index(dataset)
    client = create_client()
    result = run_rag(
        question=question.strip(),
        top_k=topK,
        model=model.strip() or None,
        client=client,
        index=index,
    )
    if result.error:
        return {"error": result.error}
    return {
        "answer": result.answer,
        "index": index,
        "sources": [
            {"rank": h.rank, "filename": h.source_filename, "page": h.page_number, "score": h.score}
            for h in result.sources
        ],
    }


# ── BM25 Query ───────────────────────────────────────────────────────

@router.post("/api/query")
async def api_query(
    query: str = Form(""),
    topK: int = Form(5),
    dataset: str = Form("nfcorpus"),
):
    if not query.strip():
        return {"error": "Query cannot be empty."}
    index = _resolve_index(dataset)
    try:
        client = create_client()
        hits = bm25_search(client, query.strip(), topK, index)
        return {
            "hits": [
                {
                    "rank": h.rank,
                    "score": h.score,
                    "doc_id": h.doc_id,
                    "filename": h.source_filename,
                    "page": h.page_number,
                    "snippet": h.snippet,
                }
                for h in hits
            ],
            "index": index,
        }
    except Exception as e:
        return {"error": str(e)}


# ── PDF Ingest ───────────────────────────────────────────────────────

@router.post("/api/ingest")
async def api_ingest(pdfPath: str = Form("")):
    path = pdfPath.strip()
    if not path:
        return {"error": "PDF path is required."}
    if not path.lower().endswith(".pdf"):
        return {"error": "File must be a .pdf"}

    p = Path(path)
    if not p.is_absolute():
        p = _REPO_ROOT / p
    if not p.exists():
        return {"error": f"File not found: {pdfPath}"}

    try:
        client = create_client()
        index = config.index_name()
        ensure_index_exists(client, index)
        pages = parse_pdf(p)
        chunks = chunk(pages)
        n = index_chunks(client, chunks, p.name, index)
        return {"chunksIndexed": n, "filename": p.name, "index": index}
    except Exception as e:
        return {"error": str(e)}


# ── Corpus Ingest (BEIR) ─────────────────────────────────────────────

@router.post("/api/corpus-ingest")
async def api_corpus_ingest(
    index: str = Query("searchlab-v0"),
    docs: list[dict] = Body(...),
):
    try:
        client = create_client()
        ensure_index_exists(client, index)
        n = index_corpus_docs(client, docs, index)
        return {"indexed": n, "index": index}
    except Exception as e:
        return {"error": str(e)}


# ── Eval SSE Stream ──────────────────────────────────────────────────

def _build_eval_command(op: str, dataset: str, slice_val: str = "", run_id: str = "") -> list[str]:
    match op:
        case "download":
            cmd = ["uv", "run", "searchlab-eval", "download", "--dataset", dataset]
            if slice_val:
                cmd += ["--slice", slice_val]
        case "ingest":
            cmd = ["uv", "run", "searchlab-eval", "ingest", "--dataset", dataset]
        case "query":
            cmd = ["uv", "run", "searchlab-eval", "query", "--dataset", dataset]
        case "metrics":
            if not run_id:
                raise ValueError("runId is required for metrics")
            cmd = ["uv", "run", "searchlab-eval", "metrics", "ir", "--run-id", run_id]
        case "ragas":
            cmd = ["uv", "run", "searchlab-eval", "ragas", "--dataset", dataset]
            if slice_val:
                cmd += ["--slice", slice_val]
        case _:
            raise ValueError(f"Unknown op: {op}")
    return cmd


@router.get("/api/eval/stream")
async def eval_stream(
    op: str = Query(...),
    dataset: str = Query("nfcorpus"),
    slice: str = Query(""),
    runId: str = Query(""),
):
    async def generator():
        try:
            cmd = _build_eval_command(op, dataset, slice, runId)
        except ValueError as e:
            yield f"event: error\ndata: Bad request: {e}\n\n"
            return

        yield f"data: $ {' '.join(cmd)}\n\n"

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(_EVAL_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        async for raw_line in proc.stdout:
            line = raw_line.decode(errors="replace").rstrip()
            yield f"data: {line}\n\n"

        rc = await proc.wait()
        if rc == 0:
            yield "event: done\ndata: 0\n\n"
        else:
            yield f"event: error\ndata: Process exited with code {rc}\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Eval Runs ────────────────────────────────────────────────────────

@router.get("/api/eval/runs")
async def eval_runs():
    runs = []
    if not _RESULTS_DIR.is_dir():
        return runs
    for d in sorted(_RESULTS_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        scores_path = d / "ir_scores.json"
        rag_path = d / "rag_scores.json"
        raw_path = d / "raw_results.json"
        has_metrics = scores_path.exists()
        has_rag = rag_path.exists()
        has_raw = raw_path.exists()
        if not has_metrics and not has_raw and not has_rag:
            continue
        entry = {
            "runId": d.name,
            "hasMetrics": has_metrics,
            "hasRagMetrics": has_rag,
            "hasRaw": has_raw,
            "dataset": "",
            "computedAt": "",
        }
        if has_metrics:
            try:
                meta = json.loads(scores_path.read_text())
                entry["dataset"] = meta.get("dataset", "")
                entry["computedAt"] = meta.get("computed_at", "")
            except Exception:
                pass
        runs.append(entry)
    return runs


# ── Eval Results ─────────────────────────────────────────────────────

@router.get("/api/eval/results")
async def eval_results(runId: str = Query("")):
    if not runId or ".." in runId or "/" in runId:
        return JSONResponse({"error": "Invalid runId"}, status_code=400)
    path = _RESULTS_DIR / runId / "ir_scores.json"
    if not path.exists():
        return JSONResponse({"error": f"Run not found: {runId}"}, status_code=404)
    return JSONResponse(json.loads(path.read_text()))


@router.get("/api/eval/rag-results")
async def eval_rag_results(runId: str = Query("")):
    if not runId or ".." in runId or "/" in runId:
        return JSONResponse({"error": "Invalid runId"}, status_code=400)
    path = _RESULTS_DIR / runId / "rag_scores.json"
    if not path.exists():
        return JSONResponse({"error": f"RAG scores not found: {runId}"}, status_code=404)
    return JSONResponse(json.loads(path.read_text()))
