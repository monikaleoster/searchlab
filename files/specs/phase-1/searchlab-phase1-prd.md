# SearchLab — Phase 1 PRD
## RAG with BM25

> Wire retrieval into a generation pipeline. Get a working RAG loop before measuring it.

---

| Field | Value |
|-------|-------|
| Document | SearchLab Phase 1 PRD |
| Phase | Phase 1: RAG with BM25 |
| Status | Draft |
| Depends On | Phase 0 (BM25 retrieval + eval harness) — COMPLETE |
| Feeds Into | Phase 2: RAG evaluation (faithfulness, context recall, answer relevancy) |
| Eval Framework | RAGAS |
| Stack | Java 21, OpenSearch 2.19.0, Python 3.12, ragas, OpenAI API, uv |

---

## 1. Context

Phase 0 delivered two things: a BM25 retrieval pipeline (`ingest` + `query` via CLI) and an eval harness that benchmarks retrieval quality against BEIR datasets. The baseline numbers are committed.

**Phase 0 baseline results:**

| Dataset | nDCG@10 | Recall@10 | MAP@10 |
|---------|---------|-----------|--------|
| nfcorpus | 0.326 | 0.139 | 0.122 |
| FiQA-2018 | 0.266 | 0.342 | 0.206 |

FiQA's Recall@10 of 0.342 means BM25 finds roughly 1 in 3 relevant passages. Phase 1 takes those retrieved passages and wires them into an LLM to generate an answer. Phase 2 will measure how good those answers are. Phase 1 just gets the loop running.

---

## 2. Objective

Wire the existing BM25 retrieval into an LLM generation step. Ship a working `rag` command that takes a natural language question, retrieves passages from OpenSearch, and returns a generated answer with source attribution.

No quality measurement in this phase. That is Phase 2. The objective here is a working pipeline end-to-end.

---

## 3. Out of Scope

| Out of scope for Phase 1 | Covered in phase |
|--------------------------|-----------------|
| RAG quality metrics (faithfulness, context recall, answer relevancy) | Phase 2 |
| Semantic or hybrid retrieval | Phase 3 |
| Re-ranking, HyDE, query expansion | Phase 4 |
| Streaming responses or web UI | Not planned |
| Fine-tuning or custom LLMs | Not planned |

---

## 4. RAG Pipeline Design

The pipeline extends the existing CLI with a new `rag` command. Internally it chains retrieval and generation sequentially.

| # | Step | Description | Output |
|---|------|-------------|--------|
| 1 | Query intake | Accept a natural language question from the CLI | question string |
| 2 | BM25 retrieval | Run existing `searchlab query` against OpenSearch, return top-K passages | List of (score, passage, source) tuples |
| 3 | Context assembly | Concatenate top-K passages into a context block with source attribution | Prompt context string |
| 4 | LLM generation | Send context + question to the LLM, receive answer | Generated answer string |
| 5 | Output | Print answer to stdout with retrieved passages and sources listed below | CLI output |

### 4.1 Context assembly

Top-K retrieved passages get concatenated into a single context block passed to the LLM prompt. Each passage is prefixed with its source filename and rank so the LLM can reference them.

- **Default K:** 5 passages. Configurable via `--top-k` flag.
- **Prompt structure:** system instruction + context block + question. No chain-of-thought, no few-shot examples.

### 4.2 LLM configuration

- Default model: `gpt-4o-mini` (cost-effective for development iteration)
- Configurable via `SEARCHLAB_LLM_MODEL` environment variable or `--model` flag
- API key passed via `OPENAI_API_KEY` environment variable
- Temperature: `0` for reproducible outputs during benchmarking

### 4.3 CLI interface

```bash
# RAG query against ingested corpus
./searchlab rag "what is dollar cost averaging"

# With explicit top-k and model
./searchlab rag "how do index funds work" --top-k 5 --model gpt-4o-mini

# Expected output format
Answer:
Dollar cost averaging is an investment strategy where...

Sources:
  [1] fiqa-corpus/doc_2847.txt  (score: 0.821)
  [2] fiqa-corpus/doc_1203.txt  (score: 0.764)
  [3] fiqa-corpus/doc_0091.txt  (score: 0.701)
```

---

## 5. Technical Requirements

### 5.1 Implementation

- New `RagCommand` class in the Java CLI, following the existing Picocli command structure
- Calls the existing `QueryCommand` internally — no duplication of retrieval logic
- HTTP client for OpenAI API calls via the official `openai-java` library or plain `HttpClient`
- Context builder assembles the prompt string from retrieved passages
- Timeout: 30 seconds for LLM call; surface a clear error on timeout

### 5.2 Prompt template

```
You are a search assistant. Answer the question using only the provided passages.
If the passages do not contain enough information, say so.

Passages:
[1] {source_1}: {passage_1}
[2] {source_2}: {passage_2}
...

Question: {question}

Answer:
```

### 5.3 Error handling

| Scenario | Behaviour |
|----------|-----------|
| Missing API key | Print clear message, exit non-zero |
| OpenSearch unavailable | Surface existing connection error from `QueryCommand` |
| LLM API error (rate limit, server error) | Print HTTP status and message, exit non-zero |
| Empty retrieval results | Print "No passages retrieved for this query", skip generation |

### 5.4 Dependencies

- No new Python dependencies for the Java CLI
- New Java dependency: `com.openai:openai-java`
- Python eval module: no changes needed; the `--rag` flag remains off until Phase 2

---

## 6. Datasets

Both datasets ingested in Phase 0 work without modification.

- **nfcorpus** — 3,633 passages, medical nutrition domain. Used for fast smoke testing locally.
- **FiQA-2018** — 57,638 passages, finance Q&A domain. Primary benchmark dataset. Questions like "what is a Roth IRA" and "how does compound interest work" are readable and verifiable without domain expertise.

FiQA is the right dataset for Phase 1 demonstration. The answers are short, factual, and a reader can check whether the generated answer is grounded in the retrieved passage without prior knowledge of finance.

---

## 7. Acceptance Criteria

| Criterion | Pass | Fail |
|-----------|------|------|
| `rag` command returns an answer for any query against FiQA corpus | Answer printed in < 30s | Error or timeout |
| Retrieved passages printed with source attribution | Filename + rank visible | No sources shown |
| `--top-k` flag controls number of retrieved passages | k=3 and k=10 both work | Flag ignored or errors |
| Works with nfcorpus and FiQA without code changes | Both return answers | Corpus-specific code required |
| LLM model configurable via env var or flag | gpt-4o and gpt-4o-mini both swap cleanly | Model hardcoded |
| README documents the full `rag` flow with example output | Reproducible on fresh clone | Missing steps or broken |

---

## 8. What Phase 1 Does Not Measure

Phase 1 produces a working RAG loop, not a measured one. The following questions are deferred to Phase 2:

- Is the generated answer faithful to the retrieved passages?
- Is the answer relevant to the question?
- How often does the LLM hallucinate or go outside the context?
- Does increasing K improve answer quality?

Running the loop first, then measuring it, keeps the scope clean. Phase 2 adds RAGAS evaluation and produces the first RAG quality numbers.

---

## 9. Definition of Done

1. `rag` command ships in the fat JAR alongside `ingest` and `query`
2. Works against both nfcorpus and FiQA without code changes
3. README updated with `rag` usage, example output, and environment variable documentation
4. Smoke test added to CI: `rag` command runs against nfcorpus and returns non-empty output
5. Phase 1 post published with example `rag` output and a note that quality measurement is Phase 2

---

## 10. Open Questions

- **Local LLM support:** Should the `rag` command support Ollama as an alternative to OpenAI? Keeps the project runnable without API costs. Defer to Phase 2 decision.
- **Context window limits:** FiQA passages average ~200 tokens. Top-5 passages fit comfortably in gpt-4o-mini context. Not a concern for Phase 1 but needs revisiting for longer corpora.
- **Prompt language:** English only for now. Not a constraint for these datasets but worth noting.

---

*SearchLab is built in public. All PRDs, benchmark results, and code are in the repo. This document is the spec for Phase 1 only.*
