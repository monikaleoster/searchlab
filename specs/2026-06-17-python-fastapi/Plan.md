# Plan — Python/FastAPI Migration

**Companion to:** `requirements.md`

Each group is a logical unit. Complete groups in order — later groups import from earlier ones. The Java service remains runnable throughout; deletion happens in Group 9 after manual validation.

---

## Group 1 — Package Scaffold

1.1 Create `searchlab/pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "searchlab"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "pymupdf>=1.24",
    "tiktoken>=0.7",
    "opensearch-py>=2.4",
    "openai>=1.30",
    "click>=8.1",
    "python-multipart>=0.0.9",
    "requests>=2.28",
]

[project.scripts]
searchlab = "searchlab.cli:cli"

[tool.hatch.build.targets.wheel]
packages = ["searchlab"]
```

1.2 Create the directory tree:
```
searchlab/searchlab/__init__.py
searchlab/searchlab/main.py
searchlab/searchlab/config.py
searchlab/searchlab/cli.py
searchlab/searchlab/opensearch/__init__.py
searchlab/searchlab/ingest/__init__.py
searchlab/searchlab/search/__init__.py
searchlab/searchlab/rag/__init__.py
searchlab/searchlab/web/__init__.py
```

1.3 Write `searchlab/searchlab/config.py`:
- `opensearch_url() -> str`: reads `OPENSEARCH_URL` env var, default `http://localhost:9200`
- `index_name() -> str`: reads `SEARCHLAB_INDEX` env var, default `searchlab-v0`
- `openai_api_key() -> str | None`: reads `OPENAI_API_KEY`
- `llm_model() -> str`: reads `SEARCHLAB_LLM_MODEL`, default `gpt-4o-mini`

1.4 Run `uv sync` inside `searchlab/`. Confirm `uv run searchlab --help` produces output (even if empty).

---

## Group 2 — OpenSearch Client + Index Bootstrap

2.1 Write `searchlab/searchlab/opensearch/client.py`:
- `create_client(url: str | None = None) -> OpenSearch`: creates an `opensearch-py` client pointing at `config.opensearch_url()` (or the passed URL); raises `RuntimeError` with a clear message if connection fails on first use

2.2 Write `searchlab/searchlab/opensearch/index_bootstrap.py`:
- `ensure_index_exists(client: OpenSearch, index: str | None = None) -> None`: checks if the index exists; creates it with the same mapping as the Java `IndexBootstrap.java` (field: `chunk_text` as text with BM25 similarity; `source_filename`, `page_number`, `chunk_position`, `ingested_at` as keyword/integer). If index already exists, no-op.
- Export the mapping dict as `INDEX_MAPPING` so tests can assert on it.

2.3 Smoke check: with docker-compose running, `uv run python -c "from searchlab.opensearch.client import create_client; print(create_client().info())"` returns cluster info.

---

## Group 3 — Ingest Pipeline

3.1 Write `searchlab/searchlab/ingest/pdf_parser.py`:
- `parse_pdf(path: Path) -> list[PageText]` where `PageText = namedtuple("PageText", ["page_number", "text"])`
- Uses `pymupdf.open(path)` — iterates pages, extracts text via `page.get_text()`
- Skips pages where `text.strip()` is empty
- Page numbers are 1-indexed (match Java `PdfParser.java` convention)

3.2 Write `searchlab/searchlab/ingest/chunker.py`:
- `chunk(pages: list[PageText]) -> list[Chunk]` where `Chunk = dataclass(text, page_number, position)`
- Uses `tiktoken.get_encoding("cl100k_base")`
- Flat token stream across all pages, tracking which page each token belongs to
- Splits into 512-token windows (no overlap), same logic as Java `Chunker.java`
- Last window may be shorter than 512 tokens

3.3 Write `searchlab/searchlab/ingest/indexer.py`:
- `index_chunks(client: OpenSearch, chunks: list[Chunk], source_filename: str, index: str) -> int`: bulk-indexes chunks; each doc has fields `chunk_id`, `chunk_text`, `source_filename`, `page_number`, `chunk_position`, `ingested_at`; returns count of indexed chunks
- `index_corpus_docs(client: OpenSearch, docs: list[dict], index: str) -> int`: accepts BEIR-format `{_id, title, text}` dicts; builds the same field layout as `ingestor.py` currently does (`chunk_text = title + " " + text`, `source_filename = _id`); batch size 500; returns total count

3.4 Write unit tests in `searchlab/tests/`:
- `test_chunker.py`: empty pages → empty list; single page with <512 tokens → single chunk; page crossing 512-token boundary → two chunks; correct page attribution on split
- `test_pdf_parser.py`: parse `../test-corpus/sample.pdf`; assert at least one `PageText` with non-empty text (integration test, mark with pytest marker `requires_file`)

---

## Group 4 — Search + RAG Pipeline

4.1 Write `searchlab/searchlab/search/bm25_searcher.py`:
- `SearchHit = dataclass(rank, score, doc_id, source_filename, page_number, snippet)`
- `search(client: OpenSearch, question: str, top_k: int, index: str) -> list[SearchHit]`: match query on `chunk_text`; maps each OpenSearch hit to `SearchHit`; `doc_id` = `hit["_id"]`, `snippet` = first 200 chars of `chunk_text`

4.2 Write `searchlab/searchlab/rag/context_builder.py`:
- `build(hits: list[SearchHit]) -> str`: replicates `ContextBuilder.java` — `[N] source_filename: snippet` format, newline-separated; returns empty string for empty list

4.3 Write `searchlab/searchlab/rag/llm_client.py`:
- `LlmClient(model: str, api_key: str | None = None)` — reads key from `config.openai_api_key()` if not passed
- `complete(system_prompt: str, user_prompt: str) -> str`: single chat completion, temperature=0, timeout=30s
- Raises `LlmTimeoutError` on timeout; raises `LlmApiError(status_code, message)` on non-2xx
- Uses `openai` Python SDK (replaces Java `HttpClient`)

4.4 Write `searchlab/searchlab/rag/models.py`:
- `RagResult = dataclass(answer: str | None, sources: list[SearchHit], error: str | None)`

4.5 Write `searchlab/searchlab/rag/__init__.py` with a `run_rag(question, top_k, model, client, index) -> RagResult` function that wires `bm25_searcher` → `context_builder` → `llm_client` together (same logic as `RagCommand.execute()` in Java). This function is called from both the CLI and the FastAPI route.

4.6 Write unit tests:
- `test_context_builder.py`: empty list → `""`; single hit → correct `[1]` format; multiple hits → sequential numbering
- `test_llm_client.py`: missing API key → `LlmApiError` or `ValueError` with clear message (use `monkeypatch` to unset env var)

---

## Group 5 — FastAPI App + Routes

5.1 Write `searchlab/searchlab/web/html.py`:
- Port the HTML string from `WebCommand.java`'s `HTML` constant verbatim into a Python `HTML: str` constant
- Replace `__OPENAI_KEY_SET__` template token with a Python format placeholder `{openai_key_set}`
- Update the header badge from `Phase 1` to `Phase 2` (or just `Python`)

5.2 Write `searchlab/searchlab/web/routes.py` as a FastAPI `APIRouter`:

**`GET /`** — serves `html.py`'s HTML with `openai_key_set` substituted; returns `HTMLResponse`

**`POST /rag`** (form: `question`, `topK`, `model`, `dataset`) — calls `run_rag()`; returns JSON matching the Java WebCommand `/rag` response shape exactly

**`POST /api/query`** (form: `query`, `topK`, `dataset`) — calls `bm25_searcher.search()`; returns `{hits: [...], index: str}` where each hit includes `doc_id`

**`POST /api/ingest`** (form: `pdfPath`) — calls `pdf_parser`, `chunker`, `indexer.index_chunks()`; returns `{chunksIndexed, filename, index}`

**`POST /api/corpus-ingest`** (JSON body: list of `{_id, title, text}`) — calls `indexer.index_corpus_docs()`; returns `{indexed, index}`

**`GET /api/eval/stream`** (query: `op`, `dataset`, `slice`, `runId`) — SSE stream; same `buildEvalCommand` logic as Java, ported to Python subprocess + asyncio (or threading); streams stdout line by line

**`GET /api/eval/runs`** — walks `searchlab-eval/results/`; returns same JSON shape as Java: `[{runId, hasMetrics, hasRagMetrics, hasRaw, dataset, computedAt}]`

**`GET /api/eval/results`** (query: `runId`) — reads `searchlab-eval/results/<runId>/ir_scores.json`; returns file contents

**`GET /api/eval/rag-results`** (query: `runId`) — reads `searchlab-eval/results/<runId>/rag_scores.json`; returns file contents

5.3 Write `searchlab/searchlab/main.py`:
```python
from fastapi import FastAPI
from .web.routes import router

def create_app() -> FastAPI:
    app = FastAPI(title="SearchLab")
    app.include_router(router)
    return app

app = create_app()
```

5.4 Smoke check: `cd searchlab && uv run uvicorn searchlab.main:app --port 8080`; navigate to `http://localhost:8080` and confirm the UI loads. The RAG tab, Query tab, and Eval tab should be visible and functional.

---

## Group 6 — CLI Entry Points + Wrapper Script

6.1 Write `searchlab/searchlab/cli.py` using Click:

```python
@click.group()
def cli(): ...

@cli.command()
@click.argument("pdf_path")
def ingest(pdf_path): ...  # calls pdf_parser + chunker + indexer directly

@cli.command()
@click.argument("question")
@click.option("--top-k", default=10)
def query(question, top_k): ...  # calls bm25_searcher, prints ranked output

@cli.command()
@click.argument("question")
@click.option("--top-k", default=5)
@click.option("--model", default=None)
def rag(question, top_k, model): ...  # calls run_rag(), prints answer + sources block

@cli.command()
@click.option("--port", default=8080)
def serve(port): ...  # calls uvicorn.run("searchlab.main:app", port=port)
```

Output format for `rag` must match the Java `RagCommand` output exactly:
```
Answer:
<answer text>

Sources:
  [1] <filename>  (score: 0.xxx)
  [2] <filename>  (score: 0.xxx)
```

6.2 Update the repo-root `./searchlab` wrapper script:
```bash
#!/bin/bash
cd "$(dirname "$0")/searchlab"
exec uv run searchlab "$@"
```
Make executable: `chmod +x searchlab`.

6.3 Smoke check: from the repo root, `./searchlab rag "what is dollar cost averaging"` against a running FiQA index returns a non-empty answer with at least one source line.

6.4 Smoke check: `./searchlab query "what is compound interest" --top-k 5` prints a ranked list.

---

## Group 7 — `searchlab-eval` REST Migration

All changes are in `searchlab-eval/`.

7.1 Add `SEARCHLAB_URL` resolution to `searchlab_eval/cli.py`:
```python
DEFAULT_SEARCHLAB_URL = os.getenv("SEARCHLAB_URL", "http://localhost:8080")
```
Add `--searchlab-url / -U` option to the `ingest` and `query` commands (replacing `--opensearch-url`). Keep `--opensearch-url` as a deprecated alias that prints a deprecation warning and maps to `--searchlab-url` for backward compat during transition.

7.2 Rewrite `searchlab_eval/ingestor.py`:
- `ingest_corpus(corpus_path, searchlab_url, index, batch_size=500) -> int`
- Reads corpus JSONL, batches docs (500 at a time), POSTs each batch to `POST {searchlab_url}/api/corpus-ingest`
- Parses `{"indexed": N}` from response; accumulates total
- `get_doc_count(searchlab_url, index) -> int`: `GET {searchlab_url}/api/eval/runs` won't have this info — use a new `GET /api/corpus-count?index=<name>` endpoint (add to Group 5 as a 7.2-dependency backfill), OR drop the doc count verification step entirely (simpler — it was informational only)
- Decision: **drop doc count verification** — the indexed count returned from POST is sufficient

7.3 Rewrite `searchlab_eval/querier.py`:
- `run_query(query_text, searchlab_url, top_k, index) -> list[dict]`
- POSTs `{query: query_text, topK: top_k, dataset: <derived from index name>}` to `POST {searchlab_url}/api/query`
- Maps response `hits` to `{doc_id, score, rank}` — uses `hit["doc_id"]` not `hit["filename"]`
- `run_queries(...)`: same outer loop as current; replaces subprocess calls with HTTP
- Remove `searchlab_bin` parameter from all function signatures

7.4 Update `pyproject.toml` in `searchlab-eval/`:
- Remove `opensearch-py` from dependencies (no longer needed)
- Keep `requests` (already present)

7.5 Update existing tests in `searchlab-eval/tests/` that mock or reference `opensearch_url` → change to `searchlab_url`. Update any fixtures accordingly.

7.6 Smoke check:
```bash
# Terminal 1 — searchlab service
cd searchlab && uv run uvicorn searchlab.main:app --port 8080

# Terminal 2 — eval harness
cd searchlab-eval
uv run searchlab-eval ingest --dataset fiqa
uv run searchlab-eval query --dataset fiqa --slice 10
```
Confirm `results/<run_id>/raw_results.json` is written with 10 query results, each having non-empty hits.

---

## Group 8 — Integration + Regression

8.1 Run the full existing IR eval end to end against both datasets:
```bash
cd searchlab-eval
uv run searchlab-eval download --dataset fiqa --slice 50
uv run searchlab-eval ingest --dataset fiqa
uv run searchlab-eval query --dataset fiqa
uv run searchlab-eval metrics ir --run-id <run_id>
```
Compare `ir_scores.json` aggregate numbers to the Phase 0 baseline. They should be equal or within ±0.001 (any larger diff signals a doc mapping bug in `index_corpus_docs`).

| Dataset | Expected nDCG@10 | Expected Recall@10 | Expected MAP@10 |
|---------|------------------|--------------------|-----------------|
| nfcorpus | ~0.326 | ~0.139 | ~0.122 |
| FiQA-2018 | ~0.266 | ~0.342 | ~0.206 |

8.2 Run the existing `searchlab-eval` test suite: `uv run pytest`. All tests must pass.

8.3 Verify the web UI end to end via browser:
- Ingest tab: ingest `test-corpus/sample.pdf` via the UI
- RAG tab: ask "what is dollar cost averaging" against FiQA; verify answer card renders
- Eval tab: click `RAG Eval` for FiQA slice 5; verify SSE log streams and run appears
- Metrics tab: load a run; verify IR panel renders; load a run with `rag_scores.json`; verify RAG panel renders below IR panel

---

## Group 9 — Java Deletion + README

Run this group only after Group 8 passes fully and Validation.md manual checklist is signed off.

9.1 Delete Java artifacts:
```bash
rm -rf src/ target/
rm pom.xml
```

9.2 Update `README.md`:
- Replace all references to `mvn`, `java -jar`, `pom.xml` with Python/uv equivalents
- Update "Getting Started" to: `cd searchlab && uv sync && uv run uvicorn searchlab.main:app`
- Update "Commands" section with the new `searchlab` CLI
- Update "Evaluation" section: `searchlab-eval` now requires the `searchlab` service running; document `SEARCHLAB_URL`
- Confirm the Phase 0 and Phase 1 benchmark rows are still present (no new numbers ship in this phase — it's a migration, not a retrieval change)

9.3 Create `posts/python-migration.md`:
- Why the migration happened
- What changed and what didn't (same endpoints, same BM25, same chunking)
- The two-package architecture

---

## Definition of Done

- [ ] `cd searchlab && uv run uvicorn searchlab.main:app --port 8080` starts without error
- [ ] `./searchlab rag "what is compound interest"` returns an answer (FiQA indexed)
- [ ] `uv run pytest` in `searchlab-eval/` passes with no regressions
- [ ] IR benchmark numbers match Phase 0 baseline within ±0.001
- [ ] Web UI: all five tabs functional (RAG, Query, Ingest, Eval, Metrics)
- [ ] `src/` and `pom.xml` deleted
- [ ] README updated and reproducible from a fresh clone
- [ ] See `Validation.md` for the full merge checklist
