# Phase 0 — Tasks

Discrete, completable tasks. Each is sized so that "done" is unambiguous.

---

## Setup

- [ ] **T-0.01** Create Maven project with Java 21, package `com.searchlab`, single-module `pom.xml`.
- [ ] **T-0.02** Add pinned dependencies: `opensearch-java:2.x`, `pdfbox:3.x`, `jtokkit:latest-stable`, `picocli:4.x`, `slf4j-simple`. Lock versions in `pom.xml`.
- [ ] **T-0.03** Add `docker-compose.yml` with `opensearchproject/opensearch:2.13.0`, single node, security disabled, port 9200 exposed. Document in README that this is dev-only.
- [ ] **T-0.04** Add `test-corpus/sample.pdf` (a public-domain document, e.g. a short paper or RFC). Commit it.
- [ ] **T-0.05** Add `.env.example` (empty for now, but the file exists so Phase 2 can drop in API keys).
- [ ] **T-0.06** Initial `README.md` skeleton with project description, prerequisites, and placeholder for the run instructions.

## OpenSearch wiring

- [ ] **T-0.07** Implement `OpenSearchClientFactory` returning a configured `OpenSearchClient` for `localhost:9200`.
- [ ] **T-0.08** Implement `IndexBootstrap.ensureIndexExists("searchlab-v0")` that checks for the index and creates it with the Phase 0 mapping if missing. Mapping defined inline (see plan section 3).
- [ ] **T-0.09** Smoke check: a `main` that connects, ensures the index, and prints "OK" on success. Use this throughout development.

## Ingestion

- [ ] **T-0.10** Implement `PdfParser.parse(Path)` returning a list of `(pageNumber, text)` records using PDFBox.
- [ ] **T-0.11** Implement `Chunker.chunk(List<PageText>)` returning a list of `Chunk(text, pageNumber, position)`. Use jtokkit `cl100k_base`, 512 tokens, no overlap.
- [ ] **T-0.12** Implement deterministic `chunkId(sourceFilename, position)` using sha256 truncated to 16 hex chars.
- [ ] **T-0.13** Implement `Indexer.index(List<Chunk>, sourceFilename)` that bulk-indexes via the OpenSearch Java client. Uses chunk IDs from T-0.12 so re-ingest overwrites.
- [ ] **T-0.14** Wire `IngestCommand` (Picocli) that takes a PDF path and runs T-0.10 → T-0.13 in sequence. Prints `Indexed N chunks from <filename>`.

## Query

- [ ] **T-0.15** Implement `Bm25Searcher.search(query, topK)` issuing a `match` query against `chunk_text` and returning ranked hits.
- [ ] **T-0.16** Implement `QueryCommand` (Picocli) that takes a query string and `--top-k` (default 5). Prints a formatted table: rank | score | source | page | snippet (200 chars).

## CLI wrapper

- [ ] **T-0.17** Build the JAR (`mvn package`) into `target/searchlab.jar` with `Main-Class` set to the Picocli entry point.
- [ ] **T-0.18** Add `./searchlab` shell wrapper script: `#!/usr/bin/env bash` + `java -jar target/searchlab.jar "$@"`. Make it executable. Mirror as `searchlab.bat` if cross-platform matters.

## Verification

- [ ] **T-0.19** Write `run-smoke.sh` that performs the end-to-end smoke test from plan section 7 against a fresh index.
- [ ] **T-0.20** Run the smoke test. Fix any failures. Re-run until clean.
- [ ] **T-0.21** Run smoke test a second time without resetting the index → confirms idempotency (FR-0.5).

## Closeout

- [ ] **T-0.22** Update README: prerequisites, `docker compose up -d`, `mvn package`, `./searchlab ingest ...`, `./searchlab query ...`. A stranger should reach a working query in 10 minutes.
- [ ] **T-0.23** Write `/posts/phase-0.md` with the LinkedIn bullets:
  - Why I'm building SearchLab in public
  - The hello-world of search: PDF → chunks → BM25 hits
  - First gotcha (the chunk-boundary issue, or whatever bit me)
  - What's next: making it measurable
- [ ] **T-0.24** Verify Definition of Done checklist from `CONSTITUTION.md` section X passes. Commit with message `Phase 0 complete`.

---

**Total:** 24 tasks. Most are 30–90 minutes. The chunker and indexer are the meatiest; everything else is glue.
