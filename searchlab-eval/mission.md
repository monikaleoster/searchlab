# Mission

## What is searchlab-eval?

`searchlab-eval` is a standalone Python evaluation module for measuring the search and retrieval quality of a running searchlab stack.

It downloads a BEIR benchmark dataset, ingests it into OpenSearch via the `searchlab ingest` CLI, queries it via the `searchlab query` CLI, computes IR and RAG metrics, and renders a self-contained HTML report — all from a single command you can run on your laptop.

## Problem it solves

Without a reproducible eval loop, every change to search configuration (analyzers, hybrid weights, re-rankers, RAG prompts) is judged by gut feel. `searchlab-eval` replaces that with a number you can compare across commits.

## Who runs it?

**Developers** — run it locally before opening a PR to confirm a config change improves (or at least doesn't regress) nDCG@10.

**Researchers / data scientists** — run it to compare retrieval strategies, slice subsets of BEIR, and explore metric breakdowns in the HTML report.

**CI** — runs it as a pytest harness and gates merges on configurable metric thresholds.

One tool, three audiences, same output.

## Core responsibilities

| Responsibility | Description |
|---|---|
| Dataset acquisition | Download a BEIR dataset (e.g. `scifact`, `nfcorpus`) and optionally slice to N queries for speed |
| Ingest | Call `searchlab ingest` as a subprocess to load corpus documents into OpenSearch |
| Query | Call `searchlab query` as a subprocess for each evaluation query; collect ranked results |
| IR metrics | Compute nDCG@k, MAP@k, Recall@k against BEIR qrels using pytrec_eval |
| RAG metrics | Compute faithfulness, answer relevancy, and context recall using ragas |
| HTML report | Render a self-contained, locally openable HTML report summarising all metrics |

## Hard constraints

- **Independent**: zero imports from the searchlab Python package. Talks to searchlab only through its CLI.
- **Locally runnable**: `uv run searchlab-eval run --dataset scifact --slice 50` must work on a developer laptop with no extra setup beyond a running OpenSearch.
- **No magic**: every intermediate artifact (downloaded corpus, query results JSON, metrics JSON) is written to disk so runs are inspectable and reproducible.
- **Small by default**: default slice size is 100 queries so a local run completes in minutes, not hours.