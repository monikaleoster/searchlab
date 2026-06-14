# Plan — Phase 1: RAG with BM25

**Companion to:** `requirements.md`

Each group is a logical unit of work. Complete groups in order — later groups depend on earlier ones compiling and passing their smoke checks.

---

## Group 1 — Dependency & Configuration

1.1 Add `com.openai:openai-java` to `pom.xml`. Confirm `mvn compile` still passes.

1.2 Add `OPENAI_API_KEY` and `SEARCHLAB_LLM_MODEL` to `.env.example` with placeholder values and inline comments explaining each.

1.3 Confirm the fat-JAR build (`mvn package`) still produces a single executable JAR. No classpath conflicts introduced.

---

## Group 2 — Context Assembly

2.1 Create `src/main/java/com/searchlab/rag/ContextBuilder.java`.
- Accepts a `List<SearchHit>` (or equivalent result type from `QueryCommand`)
- Returns a formatted context string: each passage prefixed `[N] source_filename: passage_text`
- Returns an empty string (not null) when the list is empty

2.2 Write a unit test for `ContextBuilder`:
- Empty list → empty string
- Single passage → correct `[1]` prefix with filename
- Multiple passages → sequential `[1]`, `[2]`, `[3]` numbering

---

## Group 3 — LLM Client

3.1 Create `src/main/java/com/searchlab/rag/LlmClient.java`.
- Wraps `openai-java` (or `java.net.http.HttpClient` if the library adds too much weight)
- Reads model from constructor parameter; reads API key from `OPENAI_API_KEY` env var
- Sends a single chat completion request: system instruction + context block + question
- Temperature = 0
- Timeout = 30 seconds; throws a typed `LlmTimeoutException` on breach
- Throws `LlmApiException` (wrapping HTTP status + body) on non-2xx response

3.2 Write a unit test for `LlmClient` error paths using a mock HTTP server or mocked client:
- Missing API key → `IllegalStateException` with clear message
- 429 response → `LlmApiException` surfacing status code
- Timeout → `LlmTimeoutException`

---

## Group 4 — RagCommand

4.1 Create `src/main/java/com/searchlab/cli/RagCommand.java` as a Picocli `@Command`.
- `@Parameters(index = "0")` for the question string
- `@Option("--top-k")` defaulting to 5
- `@Option("--model")` defaulting to env var `SEARCHLAB_LLM_MODEL`, fallback `gpt-4o-mini`
- Calls `QueryCommand` retrieval logic directly (no CLI subprocess)
- Delegates to `ContextBuilder` then `LlmClient`
- On empty retrieval: print `"No passages retrieved for this query."`, exit 0
- On success: print answer block then sources block (format from PRD section 4.3)

4.2 Register `RagCommand` in `Main.java` alongside `IngestCommand` and `QueryCommand`.

4.3 Manual smoke check: `./searchlab rag "what is dollar cost averaging"` against FiQA returns a non-empty answer with at least one source line.

---

## Group 5 — Error Handling & Polish

5.1 Verify all error scenarios from `requirements.md` section "Error Handling Contract" produce the correct output and exit codes. Run each scenario manually.

5.2 Ensure `RagCommand` surfaces OpenSearch connection errors from `QueryCommand` with a human-readable message (not a raw stack trace).

5.3 Confirm `--top-k 3` and `--top-k 10` both work without errors against both nfcorpus and FiQA.

---

## Group 6 — CI Smoke Test

6.1 Add a smoke test to the existing test suite (or `run-smoke.sh`) that:
- Starts OpenSearch (assumes docker-compose is up or skips with a clear message if not)
- Ingests nfcorpus (or uses the already-ingested index if available)
- Runs `./searchlab rag "what is nfcorpus about"` and asserts stdout is non-empty
- Does **not** assert answer content — only that the command completes and produces output

6.2 The smoke test must pass with `OPENAI_API_KEY` set in the environment. If the key is absent the test is skipped (not failed), with a printed explanation.

---

## Group 7 — README & Post

7.1 Update `README.md`:
- Add `rag` to the "Commands" section with usage, flags, and an example output block
- Document `OPENAI_API_KEY` and `SEARCHLAB_LLM_MODEL` under the environment variables section
- Verify the end-to-end setup instructions still work on a fresh clone path

7.2 Create `posts/phase-1.md` with LinkedIn post bullets:
- What was built (working RAG loop)
- The pipeline: BM25 retrieval → context assembly → LLM generation
- Example output snippet
- Note that quality measurement is Phase 2

---

## Definition of Done

All groups complete when:
- [ ] `mvn package` produces a fat JAR with no errors or warnings
- [ ] All unit tests pass (`mvn test`)
- [ ] Smoke test passes against nfcorpus with a real API key
- [ ] `rag` command works against both nfcorpus and FiQA without code changes
- [ ] README `rag` section is present and accurate
- [ ] `posts/phase-1.md` exists and contains the post bullets
- [ ] See `Validation.md` for the full merge checklist