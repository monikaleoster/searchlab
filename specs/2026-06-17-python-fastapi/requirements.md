# Requirements — Python/FastAPI Migration

**Feature:** Replace the Java fat-JAR with two Python modules: `searchlab` (FastAPI service + CLI) and an updated `searchlab-eval` (REST client)
**Status:** In progress
**Depends on:** Phase 1 complete (Java `rag` command, web UI), Phase 2 RAGAS eval spec exists
**Feeds into:** Phase 3 (retrieval improvements operate on the Python stack)

---

## Context

The current stack is a Java fat-JAR (`searchlab`) plus a separate Python `searchlab-eval` harness. The Java service embeds the entire web UI as an HTML string in `WebCommand.java`, exposes REST endpoints, and handles ingest/query/RAG. The eval harness calls `./searchlab` as a subprocess for queries and writes directly to OpenSearch for corpus ingestion.

This migration replaces the Java service with a Python FastAPI package, cleans up the subprocess coupling, and establishes a proper REST boundary: `searchlab` owns everything that touches OpenSearch and the LLM; `searchlab-eval` is a pure REST client that happens to also run local pytrec-eval scoring.

The Java code is not deleted until the Python version passes all manual acceptance criteria.

---

## Scope Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Service shape | REST + CLI from the same Python package | Preserves `./searchlab rag "question"` interface; eval harness and shell users don't change their mental model |
| `searchlab-eval` dependency on OpenSearch | Eliminated — all retrieval and ingestion routed through `searchlab` REST API | Clean boundary: eval has no knowledge of OpenSearch internals |
| Web UI | Keep embedded HTML, served by FastAPI | No frontend build step; UI is already functional |
| PDF parsing | `pymupdf` (fitz) | Best text extraction quality; actively maintained |
| Chunking tokenizer | `tiktoken` (cl100k_base, 512 tokens, no overlap) | Matches the Java `Chunker.java` exactly — same tokenizer, same chunk size |
| Repo structure | Two separate packages, two `pyproject.toml` | `searchlab/` and `searchlab-eval/` are independent; installed and run separately with `uv` |
| Migration strategy | Delete Java after manual validation passes | Java stays runnable throughout migration; deletion is the last step |

---

## Module Map

### `searchlab/` — New Python package (replaces `src/`, `pom.xml`, Java fat-JAR)

```
searchlab/
├── pyproject.toml
└── searchlab/
    ├── main.py               # FastAPI app factory
    ├── config.py             # env var resolution (OPENSEARCH_URL, OPENAI_API_KEY, etc.)
    ├── cli.py                # Click CLI: ingest, query, rag, serve
    ├── opensearch/
    │   ├── client.py         # OpenSearch client factory
    │   └── index_bootstrap.py
    ├── ingest/
    │   ├── pdf_parser.py     # pymupdf — replaces PdfParser.java + PageText.java
    │   ├── chunker.py        # tiktoken cl100k_base, 512 tok, no overlap — replaces Chunker.java
    │   └── indexer.py        # bulk indexing — replaces Indexer.java
    ├── search/
    │   └── bm25_searcher.py  # replaces Bm25Searcher.java + SearchHit dataclass
    ├── rag/
    │   ├── context_builder.py
    │   ├── llm_client.py
    │   └── models.py         # RagResult dataclass
    └── web/
        ├── routes.py         # FastAPI APIRouter with all endpoints
        └── html.py           # embedded HTML string (ported from WebCommand.java)
```

### `searchlab-eval/` — Modified (no longer touches OpenSearch directly)

Changed files:
- `ingestor.py` → calls `POST /api/corpus-ingest` instead of OpenSearch `/_bulk`
- `querier.py` → calls `POST /api/query` instead of `./searchlab query` subprocess
- `cli.py` → `--opensearch-url` replaced with `SEARCHLAB_URL` env var / `--searchlab-url` option on ingest and query commands
- `rag_runner.py` (Phase 2) → calls `POST /rag` instead of `./searchlab rag` subprocess

Unchanged files: `downloader.py`, `slicer.py`, `metrics/ir.py`, all tests.

---

## API Endpoints

All endpoints match the current Java `WebCommand.java` surface exactly, plus one new endpoint:

| Method | Path | Description | Consumer |
|--------|------|-------------|----------|
| GET | `/` | Serves embedded HTML UI | Browser |
| POST | `/rag` | BM25 retrieval + LLM answer | Browser UI, `searchlab-eval` ragas command |
| POST | `/api/query` | BM25 search, returns ranked hits with `doc_id` | Browser UI, `searchlab-eval` query command |
| POST | `/api/ingest` | PDF ingest (form field: `pdfPath`) | Browser UI, CLI |
| **POST** | **`/api/corpus-ingest`** | **NEW: bulk BEIR corpus ingestion (JSON array of docs)** | **`searchlab-eval` ingest command** |
| GET | `/api/eval/stream` | SSE stream for eval operations | Browser UI Eval tab |
| GET | `/api/eval/runs` | List runs with `hasMetrics` / `hasRagMetrics` flags | Browser UI |
| GET | `/api/eval/results` | IR scores for a run (`ir_scores.json`) | Browser UI |
| GET | `/api/eval/rag-results` | RAG scores for a run (`rag_scores.json`) | Browser UI |

### `/api/query` response shape — adds `doc_id`

The existing Java endpoint returns `filename` but not the OpenSearch `_id`. The Python version must return `doc_id` (the OpenSearch document `_id`) so pytrec-eval scoring against BEIR qrels works correctly. For BEIR datasets `doc_id == source_filename`, but the field must be explicit.

```json
{
  "hits": [
    {"rank": 1, "score": 0.87, "doc_id": "MED-10", "filename": "MED-10", "page": 0, "snippet": "..."}
  ],
  "index": "searchlab-fiqa"
}
```

### `/api/corpus-ingest` request/response

```json
// Request body: array of BEIR-format documents
[
  {"_id": "MED-10", "title": "...", "text": "..."},
  ...
]

// Response
{"indexed": 648, "index": "searchlab-fiqa"}
```

---

## CLI Commands (Python package entry point)

```
searchlab ingest <pdf_path>          # parse PDF, chunk, index to OpenSearch
searchlab query <question> --top-k 5 # BM25 search, print ranked results
searchlab rag <question> --top-k 5  # BM25 + LLM answer, print answer + sources
searchlab serve --port 8080          # start FastAPI server (uvicorn)
```

Installed via `pyproject.toml`:
```toml
[project.scripts]
searchlab = "searchlab.cli:cli"
```

The repo-root `./searchlab` shell script is updated to delegate to the Python CLI:
```bash
#!/bin/bash
cd "$(dirname "$0")/searchlab"
exec uv run searchlab "$@"
```

---

## Chunking Specification

Must match the Java `Chunker.java` exactly to produce equivalent indexes:
- Tokenizer: `tiktoken` `cl100k_base` encoding
- Chunk size: 512 tokens
- Overlap: none
- Page attribution: each chunk records the page number of its first token
- Document field: `chunk_text`, `page_number`, `chunk_position`, `source_filename`, `ingested_at`

---

## Environment Variables

| Variable | Default | Used by |
|----------|---------|---------|
| `OPENSEARCH_URL` | `http://localhost:9200` | `searchlab` service |
| `SEARCHLAB_INDEX` | `searchlab-v0` | `searchlab` service |
| `OPENAI_API_KEY` | — | `searchlab` service |
| `SEARCHLAB_LLM_MODEL` | `gpt-4o-mini` | `searchlab` service |
| `SEARCHLAB_LLM_JUDGE_MODEL` | `gpt-4o-mini` | `searchlab-eval` |
| `SEARCHLAB_URL` | `http://localhost:8080` | `searchlab-eval` |

`searchlab-eval` no longer needs `OPENSEARCH_URL` directly.

---

## Error Handling Contract (unchanged from Java)

| Scenario | Behaviour |
|----------|-----------|
| Missing `OPENAI_API_KEY` | Clear message, appropriate exit code |
| OpenSearch unavailable | Human-readable connection error, no stack trace exposed via API |
| LLM timeout (30s) | Clear timeout message |
| Empty BM25 results | `"No passages retrieved for this query."` — no LLM call |
| `searchlab` service unreachable (from eval) | Clear message naming the `SEARCHLAB_URL` that failed |
| Corpus ingest document error | Log the failing doc_id, continue batch |

---

## Out of Scope

| Item | Notes |
|------|-------|
| Real frontend (React/Svelte) | Embedded HTML stays |
| Authentication on FastAPI endpoints | Not in scope |
| Docker image for `searchlab` | Not in scope — local `uv run` only |
| Async OpenSearch calls | FastAPI routes can be sync; async is an optimisation for later |
| Running both Java and Python simultaneously | Java is the fallback; they share the same OpenSearch index |
