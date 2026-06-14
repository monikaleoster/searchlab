# Phase 1: RAG with BM25 — The Loop Is Running

## What was built

Phase 1 wires the existing BM25 retrieval pipeline into a full RAG loop.
A single `rag` command now takes a natural language question, retrieves passages from OpenSearch, assembles them into a prompt, calls the OpenAI API, and prints a grounded answer with source attribution.

## The pipeline

```
Question → BM25 retrieval (OpenSearch) → Context assembly → LLM generation → Answer + Sources
```

Each step is a distinct Java class:

- **`Bm25Searcher`** — already existed from Phase 0; no changes needed
- **`ContextBuilder`** — formats retrieved passages as `[N] filename: text`
- **`LlmClient`** — sends a chat completion request via `java.net.http.HttpClient`; temperature=0 for reproducibility
- **`RagCommand`** — Picocli command wiring the three steps together

## Example output

```
$ ./searchlab rag "what is dollar cost averaging" --top-k 5

Answer:
Dollar cost averaging is an investment strategy where an investor divides
the total amount to be invested across periodic purchases of a target asset
in order to reduce the impact of volatility on the overall purchase.

Sources:
  [1] fiqa-corpus/doc_2847.txt  (score: 0.821)
  [2] fiqa-corpus/doc_1203.txt  (score: 0.764)
  [3] fiqa-corpus/doc_0091.txt  (score: 0.701)
```

Works against both FiQA (finance Q&A) and nfcorpus (medical nutrition) without code changes.

## What Phase 1 does not measure

The loop runs. The quality of the answers is not yet measured.

Phase 2 will add RAGAS evaluation — faithfulness, context recall, and answer relevancy — to get the first RAG quality numbers. That is when we will know whether BM25's Recall@10 of 0.342 on FiQA actually translates into useful answers.

For now: the pipeline is alive.
