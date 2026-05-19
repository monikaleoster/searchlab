# Phase 0 — Plan

**Companion to:** `spec.md`
**Resolves:** The open questions listed in spec section 8.

---

## 1. Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Build tool | **Maven** | More predictable, ubiquitous in enterprise Java, fewer surprises. Gradle's flexibility is wasted on a project this small. |
| PDF parser | **Apache PDFBox 3.x** | Lightweight, no transitive Tika weight. Tika comes in Phase 6/7 when format breadth matters. |
| Tokenizer | **jtokkit** | A tiktoken port for JVM. Ensures chunk sizes match what embedding models will see in Phase 3. Adopting it now means Phase 3 has no surprises. |
| CLI entry | **Plain `main` class with Picocli** | Picocli is one dependency for proper argument parsing. No Spring container needed at this stage. |
| Java version | **21** | Virtual threads available for Phase 3. LTS. |
| OpenSearch version | **2.13.0** | Pinned. Latest stable at planning time. |
| OpenSearch client | **`opensearch-java` 2.x** | The current client. Never `RestHighLevelClient`. |

---

## 2. Module layout

A single Maven module is sufficient for Phase 0. Splitting into multiple modules is deferred until Phase 2 introduces the HTTP layer.

```
searchlab/
├── CONSTITUTION.md
├── README.md
├── docker-compose.yml
├── pom.xml
├── .env.example
├── test-corpus/
│   └── sample.pdf
├── specs/
│   └── phase-0/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
├── posts/
│   └── phase-0.md             # (created at phase end)
├── backlog.md
└── src/
    └── main/
        └── java/
            └── com/searchlab/
                ├── Main.java              # Picocli entry point
                ├── cli/
                │   ├── IngestCommand.java
                │   └── QueryCommand.java
                ├── ingest/
                │   ├── PdfParser.java     # wraps PDFBox
                │   ├── Chunker.java       # 512-token fixed chunking via jtokkit
                │   └── Indexer.java       # bulk indexes into OpenSearch
                ├── search/
                │   └── Bm25Searcher.java
                └── opensearch/
                    ├── OpenSearchClientFactory.java
                    └── IndexBootstrap.java   # creates index + mapping if missing
```

---

## 3. Index mapping (`searchlab-v0`)

Defined in code (`IndexBootstrap`) and asserted on startup. JSON form:

```json
{
  "mappings": {
    "properties": {
      "chunk_text":       { "type": "text", "analyzer": "standard" },
      "source_filename":  { "type": "keyword" },
      "chunk_id":         { "type": "keyword" },
      "page_number":      { "type": "integer" },
      "chunk_position":   { "type": "integer" },
      "ingested_at":      { "type": "date" }
    }
  }
}
```

`chunk_id` is deterministic: `sha256(source_filename + ":" + chunk_position)` truncated to 16 hex characters. This satisfies FR-0.5 (idempotency).

---

## 4. Chunking strategy (Phase 0 only)

- Read the entire PDF text via PDFBox, preserving page boundaries as a separate stream of `(text, page_number)` segments.
- Concatenate per-page text into a single token stream using jtokkit's `cl100k_base` encoding (matches OpenAI embedding tokenization, which is what Phase 3 will use).
- Slice into 512-token windows, no overlap.
- For each chunk, record the page number of its first token (best-effort attribution; good enough for Phase 0).

This is deliberately the simplest strategy. Phase 1's golden set will reveal where it fails, which is itself a future post.

---

## 5. `docker-compose.yml`

A single-node OpenSearch cluster with security disabled for local dev (clearly documented as dev-only). Pinned to `opensearchproject/opensearch:2.13.0`. Exposes port 9200.

---

## 6. CLI contract

```
./searchlab ingest <path-to-pdf>
  → prints: "Indexed N chunks from <filename>"
  → exit 0 on success, non-zero on parse or index failure

./searchlab query "<query string>" [--top-k 5]
  → prints a table: rank | score | source | page | snippet
  → exit 0 if at least one result; exit 0 with "no results" message if empty; non-zero on connection failure
```

The `./searchlab` wrapper is a shell script that runs `java -jar target/searchlab.jar "$@"`.

---

## 7. Testing approach

Phase 0 does not need extensive automated tests, but it needs **one end-to-end smoke test** that runs in CI (or locally via `./run-smoke.sh`):

1. Start OpenSearch via docker-compose.
2. Ingest `test-corpus/sample.pdf`.
3. Assert chunk count > 0 via the OpenSearch `_count` API.
4. Issue a query for a known phrase from the PDF.
5. Assert at least one hit and that the snippet contains the phrase.
6. Re-ingest the same PDF.
7. Assert chunk count is unchanged (idempotency).

This smoke test **is** the acceptance test. It encodes the spec's acceptance criteria as executable checks.

Unit tests are encouraged for `Chunker` (boundary cases: empty input, sub-512-token input, exactly-512-token input) but not required for ingestion glue or OpenSearch calls in Phase 0.

---

## 8. What is deliberately not in the plan

- No HTTP server.
- No frontend.
- No async / virtual threads. Phase 0 is single-threaded and that is fine.
- No metrics or observability beyond stdout logs.
- No retry logic on OpenSearch calls. If it fails, it fails loudly.

These are temptations that would dilute the phase. They appear when their phase demands them.

---

## 9. Time estimate

- Day 1: Maven project skeleton, `docker-compose.yml`, index mapping, OpenSearch client wiring, smoke test that hits an empty index.
- Day 2: PDFBox integration, jtokkit chunker, `ingest` command, deterministic chunk IDs.
- Day 3: `query` command with formatted output, end-to-end smoke test, README, post bullets.

Three focused days. If it stretches past five, the scope has crept and the spec needs revisiting.
