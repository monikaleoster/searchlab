# Backlog

Features and improvements deferred from active phases. Items here are NOT in scope until a future phase spec explicitly picks them up.

---

## Chunking

- Sentence-aware chunking (don't break mid-sentence)
- Sliding-window overlap (e.g. 64-token overlap between chunks)
- Semantic chunking

## Retrieval

- HyDE (Hypothetical Document Embeddings)
- Query classification / routing
- Metadata filtering (author, date, section)
- Multi-tenancy / per-tenant indexes

## Ingestion

- Multi-format support (Tika: DOCX, HTML, Markdown)
- Google Drive / S3 connectors
- Incremental re-index (only changed pages)

## Infrastructure

- Retry logic on OpenSearch calls
- Async / virtual-thread ingestion pipeline
- Observability (metrics, structured logs)

## UI / API

- HTTP server (Spring Boot, Thymeleaf + htmx)
- Single-page app

---

*Add items here when they feel tempting mid-phase — do not add them to the current spec.*
