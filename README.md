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
| 1 | Evaluation loop — golden set + BM25 baseline | Planned |
| 2+ | Retrieval improvements | Backlog |

---

## Environment variables

See `.env.example`. Phase 0 requires none — OpenSearch runs unauthenticated locally.
