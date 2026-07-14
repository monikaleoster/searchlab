# Validation — Phase 1: RAG with BM25

This document defines what "done" means for Phase 1 and how to verify it. Work through each section before merging to main.

---

## 1. Automated Checks

Run these first. Everything manual is irrelevant if these fail.

```bash
# Build
mvn package -q

# Unit tests
mvn test

# Smoke test (requires OPENAI_API_KEY and docker-compose up)
./run-smoke.sh   # or: mvn verify -Pintegration
```

Pass criteria:
- [ ] `mvn package` exits 0, fat JAR exists at `target/searchlab.jar`
- [ ] `mvn test` exits 0, no skipped tests without explanation
- [ ] Smoke test exits 0, stdout contains a non-empty answer string

---

## 2. Acceptance Criteria (from PRD §7)

Verify each row manually or via the smoke test. Mark pass/fail.

| # | Criterion | How to verify | Pass | Fail |
|---|-----------|---------------|------|------|
| AC-1 | `rag` command returns an answer for any FiQA query in < 30s | Run `./searchlab rag "what is compound interest"` against FiQA index, observe timing | Answer printed | Error, timeout, or no output |
| AC-2 | Retrieved passages printed with source attribution | Inspect `Sources:` block — filename + rank visible | Filename + score shown | No sources or garbled output |
| AC-3 | `--top-k` controls retrieved passages | Run `--top-k 3` and `--top-k 10`; verify source count matches | k sources shown | Flag ignored or errors |
| AC-4 | Works against nfcorpus and FiQA without code changes | Run the same command against both indexes | Both return answers | Corpus-specific handling required |
| AC-5 | LLM model configurable | Set `SEARCHLAB_LLM_MODEL=gpt-4o` and run; then pass `--model gpt-4o-mini` | Model swaps cleanly | Model hardcoded or flag ignored |
| AC-6 | README documents full `rag` flow with example output | Fresh-clone read-through; follow every step | Reproducible | Missing steps or broken |

---

## 3. Manual Verification Steps

Work through these in order with a live environment (OpenSearch running, FiQA indexed, `OPENAI_API_KEY` set).

### 3.1 Happy path — FiQA

```bash
./searchlab rag "what is dollar cost averaging"
```

Expected:
- `Answer:` block contains a coherent sentence referencing the concept
- `Sources:` block lists at least 1 entry with a filename and score
- Completes in under 30 seconds

### 3.2 Happy path — nfcorpus

```bash
./searchlab rag "what foods reduce cholesterol"
```

Expected: same structural output, different domain answer. No code changes required between runs.

### 3.3 top-k boundary checks

```bash
./searchlab rag "what is a Roth IRA" --top-k 1
./searchlab rag "what is a Roth IRA" --top-k 10
```

Expected: `Sources:` block shows 1 entry for `--top-k 1` and 10 entries for `--top-k 10`.

### 3.4 Model flag

```bash
SEARCHLAB_LLM_MODEL=gpt-4o ./searchlab rag "how do index funds work"
./searchlab rag "how do index funds work" --model gpt-4o-mini
```

Expected: both complete without error. No assertion on answer content.

### 3.5 Missing API key

```bash
OPENAI_API_KEY="" ./searchlab rag "test question"
```

Expected: clear error message printed to stderr, exit non-zero. No stack trace exposed to the user.

### 3.6 Empty retrieval

Index a corpus with a nonsense term that cannot match, then query for it:

```bash
./searchlab rag "xyzzy foobarbaz quux"
```

Expected: `"No passages retrieved for this query."` printed, exit 0, no LLM call attempted.

### 3.7 OpenSearch unavailable

Stop docker-compose, then:

```bash
./searchlab rag "what is compound interest"
```

Expected: connection error surfaced with a human-readable message, exit non-zero. No raw exception stack trace.

---

## 4. Constitution Checklist

Confirm Phase 1 satisfies the project constitution before merging.

| Rule | Check |
|------|-------|
| **Section IV — One Phase, One Win:** single objective met (working RAG loop) | [ ] |
| **Section IV — LinkedIn post bullets exist** at `posts/phase-1.md` | [ ] |
| **Section VI — Reproducibility:** `docker compose up` + README steps reach a working `rag` query | [ ] |
| **Section VII — Spec discipline:** spec, plan, tasks exist and are checked in | [ ] |
| **Section IX — No secrets in repo:** `OPENAI_API_KEY` in `.env.example` only, not committed | [ ] |
| **Section IX — README is current:** `rag` command documented with example output | [ ] |

---

## 5. Merge Gate

All of the following must be true before opening a PR to main:

- [ ] Automated checks (§1) pass
- [ ] All AC rows (§2) marked pass
- [ ] All manual steps (§3) completed without unexpected failures
- [ ] Constitution checklist (§4) fully checked
- [ ] `posts/phase-1.md` exists with at minimum 3 LinkedIn-ready bullets
- [ ] No open questions from `requirements.md` block the implementation (deferred ones logged in `backlog.md`)
- [ ] Benchmark has **not** been run — Phase 1 explicitly defers measurement to Phase 2; do not add numbers to the benchmark table until Phase 2

---

## 6. Known Deferred Items (not blockers)

These are explicitly out of scope for Phase 1. Log in `backlog.md` if not already there.

- Ollama / local LLM support (Phase 2 decision)
- Context window handling for corpora with long passages
- Streaming output
- RAG quality metrics (faithfulness, context recall, answer relevancy) — Phase 2
