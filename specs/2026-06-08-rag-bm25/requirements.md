# Requirements — Phase 1: RAG with BM25

**Phase:** 1
**Feature:** Wire BM25 retrieval into an LLM generation pipeline
**Status:** In progress
**Spec source:** `files/specs/phase-1/searchlab-phase1-prd.md`
**Depends on:** Phase 0 complete (BM25 retrieval + eval harness, baseline numbers committed)
**Feeds into:** Phase 2 — RAG evaluation with RAGAS (faithfulness, context recall, answer relevancy)

---

## Context

Phase 0 delivered a BM25 retrieval CLI (`ingest` + `query`) and an eval harness. The baseline retrieval numbers are:

| Dataset    | nDCG@10 | Recall@10 | MAP@10 |
|------------|---------|-----------|--------|
| nfcorpus   | 0.326   | 0.139     | 0.122  |
| FiQA-2018  | 0.266   | 0.342     | 0.206  |

FiQA's Recall@10 of 0.342 means BM25 retrieves roughly 1-in-3 relevant passages. Phase 1 takes those passages and feeds them to an LLM to produce a grounded answer. Phase 2 will measure quality. This phase only gets the loop running.

---

## Objective

Ship a working `rag` command in the existing fat JAR. The command accepts a natural language question, retrieves passages from OpenSearch via the existing `QueryCommand`, assembles them into a prompt, calls the OpenAI API, and prints the generated answer with source attribution.

No quality measurement ships in this phase.

---

## In Scope

- `RagCommand` Picocli class wiring `QueryCommand` → context assembly → OpenAI call → stdout output
- `--top-k` flag (default 5), `--model` flag, `OPENAI_API_KEY` env var, `SEARCHLAB_LLM_MODEL` env var
- Error handling: missing key, empty retrieval, API timeout/errors
- Works against both nfcorpus and FiQA without code changes
- README updated with `rag` usage and example output
- Smoke test: `rag` command runs against nfcorpus and returns non-empty output

## Out of Scope

| Deferred item                                      | Phase |
|----------------------------------------------------|-------|
| RAG quality metrics (faithfulness, context recall) | 2     |
| Semantic or hybrid retrieval                       | 3     |
| Re-ranking, HyDE, query expansion                  | 4     |
| Streaming responses or web UI                      | —     |
| Fine-tuning or custom LLMs                         | —     |
| Ollama / local LLM support                         | 2 (decision deferred) |

---

## Scope Decisions

**No duplication of retrieval logic.** `RagCommand` calls `QueryCommand` internally. Any future retrieval improvements automatically flow into RAG.

**Sequential pipeline only.** No async, no streaming. This is the simplest loop that works. Phase 1's job is correctness, not performance.

**Plain `HttpClient` or `openai-java`.** One new dependency: `com.openai:openai-java`. No LangChain, no LlamaIndex, no orchestration frameworks — novelty lives in the retrieval layer per the Constitution.

**Temperature = 0.** Reproducible outputs are required for the Phase 2 benchmark baseline.

**Default model: `gpt-4o-mini`.** Cost-effective for iteration. Swappable via env var or flag.

**Top-K default = 5.** FiQA passages average ~200 tokens; 5 passages fit well within gpt-4o-mini's context window.

---

## Technical Constraints (from CONSTITUTION.md)

- Java 21, Maven, Picocli — no new frameworks without a justified spec entry
- OpenSearch via `opensearch-java` client only
- No secrets in repo; API keys via environment variables documented in `.env.example`
- No retrieval change ships without a number — this phase ships the loop only; Phase 2 adds the numbers

---

## Prompt Template

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

---

## Error Handling Contract

| Scenario                            | Behaviour                                              |
|-------------------------------------|--------------------------------------------------------|
| Missing `OPENAI_API_KEY`            | Print clear message, exit non-zero                     |
| OpenSearch unavailable              | Surface existing connection error from `QueryCommand`  |
| LLM API error (rate limit / 5xx)    | Print HTTP status and message, exit non-zero           |
| Empty retrieval results             | Print "No passages retrieved for this query", skip LLM |
| LLM call exceeds 30s timeout        | Print timeout message, exit non-zero                   |