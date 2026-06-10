# SearchLab

A public learning lab for hands-on search engineering. Each phase ships one measurable improvement and one LinkedIn post.

**Phase 0 — Pipeline Alive:** PDF → chunks → BM25 hits. No magic, just plumbing.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker + Docker Compose | any recent |
| JDK | 21+ |
| Maven | 3.9+ |

Verify:
```bash
java --version   # must be 21.x
mvn --version
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

### 2. Build the JAR

```bash
mvn package -q
# → target/searchlab.jar (~22 MB fat JAR)
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
    Default top-k: 5. Default model: gpt-4o-mini.
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

---

## Smoke test

Runs all Phase 0 acceptance checks (ingest, query, idempotency) and exits 0:

```bash
./run-smoke.sh
```

---

## How it works (Phase 0)

1. **PDFBox 3.x** extracts per-page text from the PDF.
2. **jtokkit** (`cl100k_base`) tokenizes the concatenated text and slices it into 512-token windows.
3. Each chunk gets a deterministic ID: `sha256(filename + ":" + position)[:16]` — re-ingesting overwrites, never duplicates.
4. **OpenSearch `match` query** against `chunk_text` returns BM25-ranked results.

---

## Evaluation (`searchlab-eval`)

`searchlab-eval` is a standalone Python harness that measures search quality against [BEIR](https://github.com/beir-cellar/beir) benchmark datasets. It drives the `searchlab` CLI as a subprocess — no internal imports, only the published interface.

### Additional prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| uv | any recent |

### Quick start

```bash
cd searchlab-eval

# Download a BEIR dataset (nfcorpus = smallest, ~3 500 docs)
uv run searchlab-eval download --dataset nfcorpus

# Build the JAR and seed the index (skip if you already ran the main quick start)
cd .. && mvn package -q && ./searchlab ingest test-corpus/sample.pdf && cd searchlab-eval

# Ingest corpus into OpenSearch — goes into index searchlab-nfcorpus
uv run searchlab-eval ingest --dataset nfcorpus

# Run evaluation queries and collect ranked results
uv run searchlab-eval query --dataset nfcorpus
# → writes results/nfcorpus-<timestamp>/raw_results.json

# Compute IR metrics
uv run searchlab-eval metrics ir --run-id <run_id>
# → prints table; writes results/<run_id>/ir_scores.json
```

Use `--slice N` on `download` to limit to N queries for fast local iteration (default 100).

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

RAG metrics (faithfulness, answer relevancy, context recall via `ragas`) are planned for Phase 5 behind a `--rag` flag — no LLM cost unless opted in.

### Layout

```
searchlab-eval/
├── pyproject.toml              # Python 3.12, uv, all deps pinned
├── searchlab_eval/
│   ├── cli.py                  # Click entry point (download/ingest/query/metrics)
│   ├── downloader.py           # BEIR GenericDataLoader wrapper
│   ├── slicer.py               # Deterministic query subsetting
│   ├── ingestor.py             # OpenSearch _bulk ingest
│   ├── querier.py              # Query loop + result collection
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
├── pom.xml                     # Java 21, Maven, all deps pinned
├── searchlab                   # shell wrapper → target/searchlab.jar
├── run-smoke.sh                # Phase 0 acceptance test
├── test-corpus/sample.pdf      # public-domain RFC 1149 (IP over Avian Carriers)
├── specs/phase-0/              # spec.md, plan.md, tasks.md
├── searchlab-eval/             # Python evaluation harness (see above)
└── src/main/java/com/searchlab/
    ├── Main.java
    ├── cli/                    # IngestCommand, QueryCommand (Picocli)
    ├── ingest/                 # PdfParser, Chunker, Indexer, ChunkId
    ├── search/                 # Bm25Searcher
    └── opensearch/             # OpenSearchClientFactory, IndexBootstrap
```

---

## Phases

| Phase | Objective | Status |
|-------|-----------|--------|
| 0 | Pipeline alive — PDF → BM25 hits | **Done** |
| 1 | Evaluation loop — BEIR datasets + IR metrics baseline | **In progress** |
| 2+ | Retrieval improvements | Backlog |

---

## Environment variables

See `.env.example`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes (for `rag`) | — | OpenAI API key |
| `SEARCHLAB_LLM_MODEL` | No | `gpt-4o-mini` | LLM model for `rag` command |
| `OPENSEARCH_HOST` | No | `localhost` | OpenSearch host |
| `OPENSEARCH_PORT` | No | `9200` | OpenSearch port |

Phase 0 required none of these — OpenSearch runs unauthenticated locally. Phase 1 adds `OPENAI_API_KEY` for the `rag` command.
