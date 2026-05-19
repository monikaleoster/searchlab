# Phase 0 LinkedIn Post — Pipeline Alive

## Why I'm building SearchLab in public

I've been designing and shipping enterprise search systems for years, but most of that work lives behind NDAs. SearchLab is my way of doing it all in public — every decision, every measurement, every dead end.

The rules: each phase has one objective, one number (Phase 1+), and one post. No shipping without a measurement. No measurement without reproducible code.

Phase 0's job was simple: prove the pipeline runs. PDF in, BM25 hits out. Nothing interesting yet — that's the point.

---

## The hello-world of search: PDF → chunks → BM25 hits

The stack for Phase 0:
- **OpenSearch 2.19.0** (Docker, single node, security off for dev)
- **PDFBox 3.x** for PDF → per-page text
- **jtokkit** (`cl100k_base`) for tokenisation — same encoding as OpenAI embeddings, so Phase 3 has no surprises
- **512-token fixed windows**, no overlap
- **Deterministic chunk IDs**: `sha256(filename + ":" + position)[:16]` — re-ingest overwrites, never duplicates
- **Picocli** CLI, fat JAR, `./searchlab ingest` + `./searchlab query`

One smoke test encodes all four acceptance criteria. It passes. The pipeline is alive.

---

## First gotcha: chunk boundaries don't care about sentences

RFC 1149 ("IP over Avian Carriers") is only 2 pages. My chunker produced exactly 2 chunks — which means I never actually hit a mid-sentence split in Phase 0.

That's fine for now, but it's also the first thing the evaluation loop will expose: when chunks break across a key sentence, BM25 scores drop for queries that span the boundary. Phase 1 will make that visible with a golden set. Phase 2 might fix it with sentence-aware chunking.

The lesson: **fixed-window chunking is easy to implement and hard to defend.** It's the right baseline — but only because I'll measure it.

---

## What's next: making it measurable

Phase 0 built the floor. Phase 1 builds the ruler.

Next up:
- A golden set: a small set of (query, expected-chunk) pairs hand-labelled against the test corpus
- An eval harness that scores BM25 with NDCG@5 and MRR
- A benchmark table committed alongside the code

Once the ruler exists, every future phase is a comparison. That's when SearchLab stops being a tutorial and starts being a lab.

---

*Repo: github.com/[your-handle]/searchlab*
*Stack: Java 21 · OpenSearch · PDFBox · jtokkit · Picocli*
