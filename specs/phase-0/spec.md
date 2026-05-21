# Phase 0 — Pipeline Alive

**Status:** Spec
**Single objective:** Prove the ingestion → index → query pipeline works end-to-end with one PDF and BM25.

---

## 1. Why this phase exists

Before any retrieval strategy can be evaluated, the boring machinery has to exist: a running search engine, a parser that turns a PDF into searchable text, an index that holds it, and a way to query it. Phase 0 builds that machinery and nothing else.

This phase is **explicitly not interesting**. Its value is that every subsequent phase builds on a foundation that already works. Skipping it means debugging infrastructure during phases that should be about retrieval quality.

---

## 2. In scope

- Local OpenSearch instance running via Docker Compose, version pinned.
- A Java service that, given a path to a PDF, parses it, chunks it, and indexes the chunks into OpenSearch.
- A CLI command that takes a query string and returns the top-5 BM25 matches with: chunk text snippet, source filename, and BM25 score.
- A single test PDF committed to the repo (or referenced from a public URL) for reproducibility.
- A README that lets a stranger clone, run `docker compose up`, ingest the test PDF, and run a query in under 10 minutes.

---

## 3. Out of scope

These belong to later phases and must not appear in Phase 0:

- Embeddings, vectors, k-NN, semantic anything.
- Evaluation metrics. (Phase 1.)
- Chat interface, HTTP server, web UI. (Phase 2.)
- Multiple file formats. PDF only.
- Multiple documents in the index. One PDF is enough to prove the pipeline.
- Chunk overlap, sentence-aware chunking, semantic chunking. Fixed 512-token chunks, no overlap.
- Metadata extraction beyond what falls out of the parser for free (filename, page number if trivial).
- Google Drive integration. Local filesystem only.

If any of these become tempting mid-phase, they go into `/backlog.md`.

---

## 4. Functional requirements

**FR-0.1 — OpenSearch is running locally.**
Running `docker compose up` from the repo root starts OpenSearch on `localhost:9200` and the cluster reports green or yellow status.

**FR-0.2 — Index exists with the correct mapping.**
On first run, the service creates an index named `searchlab-v0` with a mapping that includes at minimum: `chunk_text` (text, analyzed with the standard analyzer), `source_filename` (keyword), `chunk_id` (keyword), `page_number` (integer, nullable).

**FR-0.3 — PDF ingestion command.**
`./searchlab ingest <path-to-pdf>` parses the PDF, splits it into 512-token chunks (no overlap), and indexes each chunk as a document. Returns the number of chunks indexed and exits non-zero on failure.

**FR-0.4 — Query command.**
`./searchlab query "<query string>"` issues a `match` query against `chunk_text`, returns the top 5 results, and prints for each: rank, BM25 score, source filename, page number (if available), and a 200-character snippet of the chunk.

**FR-0.5 — Idempotency.**
Re-ingesting the same PDF does not produce duplicate chunks. Either the index is cleared on re-ingest of the same source, or chunk IDs are deterministic (e.g. hash of source + chunk position) so they overwrite.

---

## 5. Non-functional requirements

**NFR-0.1 — Reproducibility.** A fresh clone on a machine with Docker and JDK 21 must work without manual setup beyond what the README documents.

**NFR-0.2 — Pinned versions.** OpenSearch version, Java version, and all Maven/Gradle dependencies are pinned. No `latest` tags.

**NFR-0.3 — Single-command bootstrap.** Setup is at most: `docker compose up -d`, then `./searchlab ingest <pdf>`. No additional manual steps.

**NFR-0.4 — Visible failure.** If OpenSearch is unreachable or the PDF cannot be parsed, the CLI prints a clear error and exits non-zero. No silent failures.

---

## 6. Acceptance criteria

Phase 0 ships when:

1. `docker compose up -d` brings up OpenSearch and `curl localhost:9200` returns a valid cluster response.
2. `./searchlab ingest test-corpus/sample.pdf` succeeds and reports a chunk count > 0.
3. `./searchlab query "<a phrase known to be in the PDF>"` returns at least one hit whose snippet contains the phrase.
4. Re-running ingest on the same PDF does not double-count chunks (verified by `_count` on the index).
5. README walks a stranger through steps 1–3.
6. `/posts/phase-0.md` exists with the LinkedIn post bullets.
7. The constitution's Definition of Done checklist passes.

---

## 7. Risks and decisions deferred

- **PDF parser choice.** PDFBox vs Tika is decided in the plan, not the spec. The spec only requires that the parser handles a normal text PDF.
- **Build tool.** Maven vs Gradle is a plan decision; whichever is chosen is locked for the project.
- **Chunking edge cases.** A 512-token chunk may end mid-sentence. This is acceptable for Phase 0 and is explicitly a teaser for the Phase 0 LinkedIn post ("first gotcha").

---

## 8. Open questions (must resolve in plan)

- Maven or Gradle?
- PDFBox or Tika for PDF parsing?
- Which tokenizer for chunk size measurement? (`jtokkit` is the leading candidate per the constitution's stack notes.)
- Does the CLI run as a separate Spring Boot app, a `CommandLineRunner`, or a plain `main` class? (Lean: plain `main` until a reason to do otherwise emerges.)
