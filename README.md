# SearchLab

A public learning lab for hands-on search engineering. Each phase ships one measurable improvement and one LinkedIn post.

**Phase 0 — Pipeline Alive:** PDF → chunks → BM25 hits. No magic, just plumbing.

**Phase 1 — RAG Loop:** BM25 retrieval → context assembly → OpenAI generation → grounded answer with sources.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker + Docker Compose | any recent |
| Python | 3.12+ |
| uv | any recent |

Verify:
```bash
python3 --version   # must be 3.12.x or higher
uv --version
docker --version
```

---

## Quick start (≤ 10 minutes)

### 1. Start OpenSearch

```bash
docker compose up -d
```

Wait ~20 seconds, then confirm it's healthy:

```bash
curl http://localhost:9200
# → JSON with cluster_name, version 2.19.0, etc.
```

> **Note:** Security is disabled. This is a local dev setup — do not expose port 9200 externally.

### 2. Install the Python package

```bash
cd service && uv sync
```

### 3. Ingest the sample PDF

```bash
./searchlab ingest test-corpus/sample.pdf
# → Indexed 2 chunks from sample.pdf
```

### 4. Run a query

```bash
./searchlab query "avian carriers"
```

Expected output:
```
Rank  Score    Source                          Page  Snippet
----------------------------------------------------------------------------------------------------
1     0.6442   sample.pdf                      1     Network Working Group ...
2     0.4716   sample.pdf                      2      1 April 1990    regenerating ...
```

---

## Commands

```bash
./searchlab ingest <path-to-pdf>
    Parse, chunk (512 tokens, no overlap), and index a PDF.
    Prints: "Indexed N chunks from <filename>"
    Exit 0 on success, non-zero on failure.

./searchlab query "<text>" [--top-k N]
    BM25 search against indexed chunks.
    Prints: rank | score | source | page | 200-char snippet
    Default top-k: 5

./searchlab rag "<question>" [--top-k N] [--model <model>]
    Retrieve top-K passages via BM25, assemble them into a prompt,
    call the OpenAI API, and print the generated answer with sources.
    Requires OPENAI_API_KEY environment variable.
    Default top-k: 5. Default model: gpt-4o-mini (override via --model or SEARCHLAB_LLM_MODEL).

./searchlab serve [--port N]
    Launch a local web UI at http://localhost:8080.
    Tabs: RAG (with dataset selector) | Query | Ingest | Eval | Metrics
    RAG tab: select nfcorpus, FiQA-2018, or the default index, enter a question,
    get a grounded LLM answer with source attribution.
    Eval tab: download / ingest / query / compute metrics via live log stream.
    Metrics tab: per-query sortable table, compare two runs side-by-side.
    Default port: 8080. Requires OPENAI_API_KEY for the RAG tab.
```

### `rag` example

```bash
export OPENAI_API_KEY=sk-...
./searchlab rag "what is dollar cost averaging" --top-k 5
```

Expected output:
```
Answer:
Dollar cost averaging is an investment strategy where an investor divides
the total amount to be invested across periodic purchases of a target asset
in order to reduce the impact of volatility on the overall purchase.

Sources:
  [1] fiqa-corpus/doc_2847.txt  (score: 0.821)
  [2] fiqa-corpus/doc_1203.txt  (score: 0.764)
  [3] fiqa-corpus/doc_0091.txt  (score: 0.701)
```

### `serve` example

```bash
export OPENAI_API_KEY=sk-...
./searchlab serve
# → SearchLab UI → http://localhost:8080
```

Open `http://localhost:8080` in a browser. The page shows:
- A question input that POSTs to the RAG pipeline (no page reload)
- The generated answer and source citations
- IR evaluation metric tables (nDCG, Recall, MAP) auto-loaded from `searchlab-eval/results/`

---

## Smoke test

Runs all acceptance checks and exits 0:

```bash
./run-smoke.sh
```

Checks performed:
1. OpenSearch reachable
2. Ingest a PDF → chunk count > 0
3. Query returns ranked results
4. Re-ingest is idempotent
5. `rag` command returns non-empty output (skipped if `OPENAI_API_KEY` is absent)

```bash
# Run with RAG smoke check enabled
OPENAI_API_KEY=sk-... ./run-smoke.sh
```

---

## How it works

### Phase 0 — Ingestion & BM25 retrieval

1. **pymupdf** extracts per-page text from the PDF.
2. **tiktoken** (`cl100k_base`) tokenizes the concatenated text and slices it into 512-token windows.
3. Each chunk gets a deterministic ID: `sha256(filename + ":" + position)[:16]` — re-ingesting overwrites, never duplicates.
4. **OpenSearch `match` query** against `chunk_text` returns BM25-ranked results.

### Phase 1 — RAG pipeline

1. `rag` calls the existing BM25 retrieval directly — no subprocess.
2. **`context_builder`** formats the top-K hits as numbered passages: `[N] filename: snippet`.
3. A two-part prompt is sent to the OpenAI Chat Completions API:
   - **System:** _"You are a search assistant. Answer the question using only the provided passages."_
   - **User:** the formatted passages block + the question
4. Temperature is fixed at `0` for reproducible outputs (required for Phase 2 benchmarking).
5. The answer is printed with source attribution (filename, rank, BM25 score).

#### Error handling

| Scenario | Behaviour |
|---|---|
| Missing `OPENAI_API_KEY` | Print clear message, exit 1 |
| Empty retrieval results | Print "No passages retrieved", exit 0 (skip LLM) |
| LLM API error (4xx/5xx) | Print HTTP status + message, exit 1 |
| LLM timeout (> 30 s) | Print timeout message, exit 1 |
| OpenSearch unavailable | Human-readable connection error, exit 1 |

---

## Evaluation (`searchlab-eval`)

`searchlab-eval` is a standalone Python harness that measures search quality against [BEIR](https://github.com/beir-cellar/beir) benchmark datasets. It communicates with the `searchlab` REST API — no direct OpenSearch access, no subprocess calls.

**Prerequisite:** the `searchlab` service must be running (`./searchlab serve`) before running `ingest` or `query` commands.

### Additional prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| uv | any recent |

### Quick start

```bash
# Start the searchlab service (in a separate terminal)
./searchlab serve

cd searchlab-eval

# Download a BEIR dataset (nfcorpus = smallest, ~3 500 docs)
uv run searchlab-eval download --dataset nfcorpus

# Ingest corpus via the searchlab REST API
uv run searchlab-eval ingest --dataset nfcorpus

# Run evaluation queries and collect ranked results
uv run searchlab-eval query --dataset nfcorpus
# → writes results/nfcorpus-<timestamp>/raw_results.json

# Compute IR metrics
uv run searchlab-eval metrics ir --run-id <run_id>
# → prints table; writes results/<run_id>/ir_scores.json
```

Use `--slice N` on `download` to limit to N queries for fast local iteration (default 100).

The `SEARCHLAB_URL` environment variable (default `http://localhost:8080`) controls which service the eval harness talks to. Pass `--searchlab-url` to override per-command.

### Multiple datasets

Each dataset gets its own OpenSearch index (`searchlab-<dataset>`) so runs never interfere:

```bash
# Download and ingest both datasets
uv run searchlab-eval download --dataset nfcorpus
uv run searchlab-eval download --dataset fiqa

uv run searchlab-eval ingest --dataset nfcorpus   # → index: searchlab-nfcorpus
uv run searchlab-eval ingest --dataset fiqa        # → index: searchlab-fiqa

# Query and score each independently
uv run searchlab-eval query --dataset nfcorpus
uv run searchlab-eval query --dataset fiqa
```

Override the index name with `--index <name>` if needed.

### Metrics

| Metric | Cut-offs |
|--------|----------|
| nDCG | @1, @3, @5, @10 |
| MAP | @10 |
| Recall | @5, @10 |

RAG metrics (faithfulness, answer relevancy, context recall via `ragas`) are planned for Phase 2 behind a `--rag` flag — no LLM cost unless opted in.

### Layout

```
searchlab-eval/
├── pyproject.toml              # Python 3.12, uv, all deps pinned
├── searchlab_eval/
│   ├── cli.py                  # Click entry point (download/ingest/query/metrics)
│   ├── downloader.py           # BEIR GenericDataLoader wrapper
│   ├── slicer.py               # Deterministic query subsetting
│   ├── ingestor.py             # REST client → POST /api/corpus-ingest
│   ├── querier.py              # REST client → POST /api/query
│   └── metrics/
│       └── ir.py               # pytrec_eval wrapper (nDCG, MAP, Recall)
├── tests/                      # pytest suite (offline + integration-tagged)
├── data/                       # Downloaded BEIR datasets (git-ignored)
├── results/                    # Eval run outputs (git-ignored)
└── specs/                      # Per-phase requirements and plans
```

### Eval phases

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 | Scaffold — `searchlab-eval --help` works | **Done** |
| 1 | Dataset download — `download --dataset <name>` | **Done** |
| 2 | Ingest — `ingest --dataset <name>` | **Done** |
| 3 | Query — `query --dataset <name>` → `raw_results.json` | **Done** |
| 4 | IR metrics — `metrics ir --run-id <id>` → `ir_scores.json` | **Done** |
| 5 | RAG metrics — faithfulness, answer relevancy, context recall | Planned |
| 6 | HTML report — self-contained `report.html` | Planned |
| 7 | End-to-end CLI — `run --dataset <name>` orchestrates 1–6 | Planned |
| 8 | CI / pytest harness — metric threshold gating | Planned |

---

## Project layout

```
searchlab/
├── CONSTITUTION.md             # non-negotiable project principles
├── README.md
├── docker-compose.yml          # OpenSearch 2.19.0, single-node, dev-only
├── searchlab                   # shell wrapper → service/ Python package
├── run-smoke.sh                # acceptance test (Phase 0 + Phase 1 RAG check)
├── test-corpus/sample.pdf      # public-domain RFC 1149 (IP over Avian Carriers)
├── specs/                      # per-phase requirements and plans
├── service/                    # Python FastAPI service + CLI
│   ├── pyproject.toml
│   └── searchlab/
│       ├── main.py             # FastAPI app factory
│       ├── config.py           # env var resolution
│       ├── cli.py              # Click CLI: ingest, query, rag, serve
│       ├── opensearch/         # client factory, index bootstrap
│       ├── ingest/             # pdf_parser (pymupdf), chunker (tiktoken), indexer
│       ├── search/             # bm25_searcher
│       ├── rag/                # context_builder, llm_client, models
│       └── web/                # FastAPI routes, embedded HTML UI
└── searchlab-eval/             # Python evaluation harness (see above)
```

---

## Phases

| Phase | Objective | Status |
|-------|-----------|--------|
| 0 | Pipeline alive — PDF → BM25 hits | **Done** |
| 1 | RAG loop — BM25 retrieval → LLM generation → grounded answer | **Done** |
| 2 | RAG evaluation — faithfulness, context recall, answer relevancy (RAGAS) | Planned |
| 3 | Hybrid / semantic retrieval | Planned |
| 4+ | Re-ranking, HyDE, query expansion | Backlog |

### Phase 1 baseline IR numbers (BM25, no re-ranking)

| Dataset | nDCG@10 | Recall@10 | MAP@10 |
|---------|---------|-----------|--------|
| nfcorpus | 0.328 | 0.140 | 0.122 |
| FiQA-2018 | 0.266 | 0.342 | 0.206 |

These are the retrieval numbers feeding the Phase 1 RAG pipeline. Phase 2 will measure answer quality on top of these.

---

## Environment variables

See `.env.example`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes (for `rag`) | — | OpenAI API key |
| `SEARCHLAB_LLM_MODEL` | No | `gpt-4o-mini` | LLM model for `rag` command |
| `OPENSEARCH_URL` | No | `http://localhost:9200` | OpenSearch connection URL |
| `SEARCHLAB_INDEX` | No | `searchlab-v0` | Default OpenSearch index name |
| `SEARCHLAB_URL` | No | `http://localhost:8080` | `searchlab` service URL (used by `searchlab-eval`) |
