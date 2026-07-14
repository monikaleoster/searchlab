# I'm Building a Search Lab in Public — Here's Why and How It Works

Most of my search engineering work lives behind NDAs.

Years of designing and shipping enterprise retrieval systems — analyzers, hybrid ranking, re-rankers, RAG pipelines — and the only thing I can point to publicly is a LinkedIn headline. That's a frustrating place to be when you want to demonstrate what you actually know, not just claim it.

So I decided to fix that. **SearchLab** is me doing all of it in public — every decision, every measurement, every dead end — one phase at a time.

This is the first post in the series. By the end you'll know what I've built so far, how to run it yourself, and where it's going.

---

## The rules I'm holding myself to

Before I show you the code, the rules matter — because they're what separate this from yet another GitHub repo that goes stale after three commits.

**One phase, one objective, one post.** Each phase ships exactly one thing. If a phase has two goals, it's two phases. This post covers Phase 0 and the eval scaffolding (Phase 1 of the eval module).

**No retrieval change ships without a number.** This is the rule that makes it a *lab* and not a tutorial. Every change to search configuration — chunking strategy, analyzers, hybrid weights, re-rankers — must be measured against a golden set and produce a row in a benchmark table. Gut feel isn't a number.

**The evaluation loop ships before anything interesting.** Phase 0 built the pipeline. The eval module (already underway) builds the ruler. Every future phase is a comparison. Without the ruler, you're just guessing.

---

## What's been built: Phase 0

Phase 0 had one job: **prove the pipeline runs**. PDF in. BM25 hits out. Nothing clever yet — that's the point.

The stack is deliberately boring:

- **OpenSearch 2.19.0** running in Docker — the only datastore
- **PDFBox 3.x** for PDF → per-page text extraction
- **jtokkit** (`cl100k_base` encoding) for tokenisation — the same encoding OpenAI embeddings use, so later phases have no tokenisation surprises
- **512-token fixed windows**, no overlap — the simplest possible chunking
- **Deterministic chunk IDs**: `sha256(filename + ":" + position)[:16]` — re-ingesting the same PDF overwrites cleanly, never duplicates
- **Java 21 CLI** (Picocli, fat JAR) — two commands: `ingest` and `query`

Here's what it looks like to use it:

```bash
# Start OpenSearch
docker compose up -d

# Ingest a PDF
./searchlab ingest test-corpus/sample.pdf
# → Indexed 2 chunks from sample.pdf

# Query
./searchlab query "avian carriers"
```

```
Rank  Score    Source       Page  Snippet
-------------------------------------------------------------
1     0.6442   sample.pdf   1     Network Working Group ...
2     0.4716   sample.pdf   2      1 April 1990  regenerating ...
```

The test corpus is RFC 1149 — "IP over Avian Carriers." Two pages, two chunks, BM25 scores returned. The pipeline is alive.

The whole thing runs in under 10 minutes on a fresh clone. If it doesn't, that's a bug in the README, not an acceptable setup cost.

---

## What's in progress: the eval module

Phase 0 proved the plumbing works. The eval module — `searchlab-eval` — is what turns this into a lab.

The problem it solves: without a reproducible measurement loop, every change to search configuration is judged by gut feel. Did that new chunking strategy help? Probably? Maybe? The eval module replaces "probably" with a number you can commit alongside the code.

Here's what it does, end-to-end:

1. **Downloads a BEIR benchmark dataset** (e.g. `scifact`, `nfcorpus`) — real IR benchmarks with corpus, queries, and relevance judgements
2. **Ingests the corpus** into OpenSearch via the `searchlab ingest` CLI
3. **Runs all evaluation queries** through `searchlab query` and collects ranked results
4. **Computes IR metrics** — nDCG@10, MAP@10, Recall@10 — using `pytrec_eval` against the BEIR qrels
5. **Optionally computes RAG metrics** — faithfulness, answer relevancy, context recall — using `ragas` (behind a `--rag` flag, so there's no LLM cost unless you want it)
6. **Renders a self-contained HTML report** — no server, no CDN, opens in any browser

The single command that runs all of this:

```bash
uv run searchlab-eval run --dataset scifact --slice 50
```

Slice 50 queries. Run on a laptop. Finish in minutes. Get a number.

Three audiences, one tool: developers confirm a config change doesn't regress nDCG before opening a PR; researchers explore metric breakdowns across retrieval strategies; CI gates merges on configurable thresholds committed to the repo.

---

## Why the eval module ships before the interesting stuff

This is the decision I'm most deliberate about, and the one I most often see skipped.

The temptation is to do the interesting work first — semantic search, HyDE, re-rankers — and bolt on evaluation later "when it matters." That never works. By the time you add measurement, you've already made a dozen unjustified decisions that you can't retroactively score.

The ruler has to exist before the comparisons do. That's why the eval module is Phase 1, not Phase 5.

Once it's done, every future phase is a row in a table:

| Phase | Change | nDCG@10 | Recall@10 |
|-------|--------|---------|-----------|
| 0 | BM25 baseline | *TBD* | *TBD* |
| 2 | Sentence-aware chunking | ? | ? |
| 3 | Semantic retrieval | ? | ? |

That table is the point of this whole project.

---

## What's coming next

The phases in the queue:

- **Complete the eval module** — IR metrics, HTML report, end-to-end CLI command, CI/pytest harness
- **BM25 baseline committed** — first real number in the benchmark table
- **Sentence-aware chunking** — fixed windows break across key sentences; Phase 2 will make that visible and then fix it
- **Semantic retrieval** — embeddings, vector search, hybrid ranking
- **Re-ranking and RAG** — the expensive stuff, evaluated against the same benchmark so we know if it actually helps

Each phase: one objective, one number, one post.

---

## How to follow along

The repo is public. Everything is in there — specs, plans, code, benchmark results, and these posts. The `CONSTITUTION.md` at the root is the document I hold myself to; if you want to understand the design philosophy, start there.

Clone it, run the smoke test, break something, open an issue. That's what it's for.

*Stack: Java 21 · OpenSearch 2.19.0 · PDFBox · jtokkit · Picocli · Python 3.12 · BEIR · pytrec_eval · ragas · uv*
