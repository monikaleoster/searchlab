# Prompt History

Recorded per CONSTITUTION.md §VII — a session without a recorded prompt did not happen.

---

## Session 1 — Phase 0 Implementation (2026-05-18)

**Model:** Claude Sonnet 4.6
**Branch:** JSL-24464-Wiki-Search

**Prompt summary:**
> Specification-driven development session implementing Phase 0 of SearchLab.
> Instructions: read CONSTITUTION.md, specs/phase-0/{spec,plan,tasks}.md in full;
> work through all 24 tasks in order; never implement Phase 1+ features;
> confirm understanding by summarising Phase 0's single objective before starting T-0.01.

**Outcome:** All 24 tasks completed. Smoke test passes. Phase 0 Definition of Done verified.

**Deviations from plan (with rationale):**
- OpenSearch version changed from `2.13.0` → `2.19.0`: `2.13.0` image not cached locally; `2.19.0` was available and is a later stable release of the same major version. Wire protocol identical. Pin updated in `docker-compose.yml`.

---

## Session 2 — Per-Query Run Comparison (2026-07-11)

**Model:** Claude Sonnet 5
**Branch:** 2026-07-11-run-comparison

**Prompt summary:**
> Implement `specs/2026-07-11-run-comparison/` (requirements.md, Plan.md, Validation.md):
> a new read-only `GET /api/eval/compare` endpoint plus a Compare tab in the embedded UI,
> letting a user pick two runs of the same type (IR or RAG) and dataset and see per-query
> metric deltas and underlying content side by side.

**Outcome:**
- New `service/searchlab/web/compare.py`: `compare_ir` / `compare_rag`, joining IR runs by
  `query_id` and RAG runs by list position, with `only_in_a`/`only_in_b` coverage-mismatch
  lists and per-measure `delta = b - a`.
- New `GET /api/eval/compare?type=ir|rag&runA=&runB=` route in `routes.py` (404 for a
  genuinely missing run directory, 400 for dataset mismatch or a run missing the requested
  type's score file).
- New Compare tab in `web/html.py`: type/dataset/run pickers, sortable A/B/Δ table
  (default-sorted worst-regression-first), accordion row expansion for RAG
  question/answer/contexts/ground_truth or IR ranked sources, separate coverage-mismatch
  section.
- 9 new unit tests in `tests/test_compare.py` covering matched rows, only-in-A/B, dataset
  mismatch, and missing-run cases for both types; full suite (22 tests) passes.
- Verified end-to-end in a real browser against existing `nfcorpus`/`nfcorpus-ragas` runs in
  `searchlab-eval/results/`: happy path, row expansion, RAG slice-size mismatch surfacing
  extra rows in `only_in_b`, and the same-run-selected error banner.
- `docs/wiki.md` updated: §3.6 (web layer), new §4.6 workflow, new `GET /api/eval/compare`
  data-flow entry.

**Deviations from plan (with rationale):**
- `eval_runs()` in `routes.py` previously only populated a run's `dataset`/`computedAt` from
  `ir_scores.json`. RAG-only runs (no `ir_scores.json`) had `dataset: ""`, which would have
  made the Compare tab's dataset dropdown empty for RAG. Added a fallback to read
  `dataset`/`computed_at` from `rag_scores.json` when `ir_scores.json` is absent — not in the
  plan, but required for F6/AC9 (dataset-filtered run dropdowns) to work for RAG at all.
- Plan.md §2.1 said missing-file errors (`FileNotFoundError`) should map to 404, but
  Validation.md AC4 expects 400 for the "wrong type for one run" case. Resolved by
  distinguishing two failure modes in the route: run directory absent entirely → 404 (AC5);
  run directory exists but lacks the requested type's score file → 400 (AC4), since the
  latter is a type mismatch, not a missing run.

---

## Session 3 — Run Comparison Amendment: Metric Filter, Query Text, Doc Fetch (2026-07-11)

**Model:** Claude Sonnet 5
**Branch:** 2026-07-11-run-comparison

**Prompt summary:**
> Implement the un-completed tasks from `specs/2026-07-11-run-comparison/`. Groups 1–7
> (the base Compare tab) were already implemented in this branch; only the 2026-07-11
> amendment — Group 8 (metric filter dropdown, query text display, doc_id fetch-on-click) —
> remained.

**Outcome:**
- `web/compare.py`: added `_load_queries()` (BEIR `queries.jsonl` → `query_id → text` map,
  empty dict if missing) and `load_document()` (BEIR `corpus.jsonl` lookup by `_id`, raises
  `FileNotFoundError` for a missing dataset dir or unmatched `doc_id`). `compare_ir` now
  attaches `query_text` to every row/`only_in_a`/`only_in_b` entry; `compare_rag` attaches
  `query_text` (Run A's `question`) plus a `query_text_mismatch: true` flag when Run A's and
  Run B's `question` differ at the same position.
- `routes.py`: new `GET /api/eval/document?dataset=&docId=` — same `..`/`/` validation as the
  other eval routes, 404 on `FileNotFoundError`.
- `web/html.py`: metric filter `<select>` (disabled until a comparison runs, populated from
  the response's `measures`) that narrows the table to one measure's A/B/Δ columns without
  touching sort order, row order, or triggering a re-fetch — applied identically to the
  only-in-A/B tables. Query column now renders `query_text` for both IR (under the
  `query_id`) and RAG (in place of the bare index), with a visible warning block for
  RAG question mismatches. IR source-list rows are now clickable: click fetches
  `GET /api/eval/document`, inlines `title`/`text` under the entry (loading state, inline
  404 message on failure), toggles closed on a second click, and caches responses in a
  module-level `Map` keyed by `(dataset, doc_id)` for the session.
- 8 new unit tests in `tests/test_compare.py` (`query_text` attachment for IR incl. missing
  `queries.jsonl`, RAG mismatch flagging, `load_document` found/missing-doc/missing-dataset);
  full suite (29 tests) passes.
- Verified end-to-end in a real browser: started the server, ran an IR comparison
  (`nfcorpus-20260619T200023Z` vs `nfcorpus-20260623T002234Z`) and confirmed query text
  renders per row, the metric dropdown narrows to `ndcg_cut_10` A/B/Δ while preserving row
  order/sort, and clicking `MED-14` under an expanded row's Run A sources inlines its
  title/text (matching a direct `curl` of the new endpoint), collapses on a second click, and
  populates the client-side cache. Also ran a RAG comparison
  (`nfcorpus-ragas-20260623T060215Z` vs `nfcorpus-ragas-20260625T174021Z`) and confirmed
  `question` text is visible in the main table row without expanding. No console errors.
- `docs/wiki.md` updated: §4.6 workflow steps 8–10 for the amendment behaviors, and
  `GET /api/eval/compare`'s response example plus a new `GET /api/eval/document` reference
  entry.

**Deviations from plan (with rationale):** none — the amendment's contract (additive fields
only, no changes to `/api/eval/compare`'s existing shape) was followed as specified.

---

## Session 4 — Run Comparison Amendment 2: Judgement Panel (2026-07-11)

**Model:** Claude Sonnet 5
**Branch:** 2026-07-11-run-comparison

**Prompt summary:**
> Implement the un-completed tasks from `specs/2026-07-11-run-comparison/`. Groups 1–8 (base
> Compare tab plus the metric-filter/query-text/doc-fetch amendment) were already implemented
> in this branch; only Group 9 — Amendment 2, the Judgement panel (qrels for IR, `ground_truth`
> for RAG) — remained. Confirmed via `grep -ni judg` across `compare.py`/`routes.py`/`html.py`
> that nothing from this amendment existed yet.

**Outcome:**
- `web/compare.py`: added `load_qrels(dataset, query_id)` — reads BEIR
  `qrels/test.tsv` (header row skipped, tab-separated `query-id`/`corpus-id`/`score`), filters
  to the requested `query_id`, returns `[{doc_id, score}, ...]`; raises `FileNotFoundError` if
  the dataset dir or `qrels/test.tsv` is missing, returns `[]` (not an error) for a query with
  zero judged docs. `compare_rag` now attaches a row-level `ground_truth` (from `content_a`'s
  `ground_truth`) and `ground_truth_mismatch: true` when Run A's and Run B's `ground_truth`
  differ at the same position — same pattern as the existing `query_text`/`query_text_mismatch`
  fields.
- `routes.py`: new `GET /api/eval/judgement?dataset=&queryId=` — same `..`/`/` validation as
  the other eval routes, 404 on `FileNotFoundError`, otherwise `200` with
  `{query_id, judgements}` (possibly an empty list).
- `web/html.py`: every comparison row (IR and RAG) now has a "Judgement" link next to the query
  text, rendered via a shared `judgementLink()` helper with `event.stopPropagation()` so it
  doesn't also trigger the row's content-expansion toggle. Clicking it toggles a row into a new
  `cmpOpenJudgements` `Set`, rendered as its own `<tr class="cmp-judgement-row">` — independent
  of `cmpExpandedKey` (the content-expansion accordion), so multiple Judgement panels and a
  row's own content expansion can all be open simultaneously. IR fetches
  `GET /api/eval/judgement` on first open and caches by `(dataset, query_id)` in a
  `cmpJudgementCache` `Map` (mirroring the existing `cmpDocCache` pattern from Session 3); RAG
  renders `row.ground_truth`/`ground_truth_mismatch` directly from the already-fetched compare
  response, no request. Removed `ground_truth` from the RAG row-expansion's per-run Run A/Run B
  columns (`renderCompareRowContent`) since it's no longer duplicated there — those columns now
  show `answer`/`contexts` only.
- 5 new unit tests in `tests/test_compare.py` (`load_qrels` found/no-match/missing-dataset,
  `compare_rag` ground_truth attachment + mismatch flagging); full suite (33 tests) passes.
- Verified end-to-end in a real browser against a locally running server (port 8081, to avoid
  disturbing an already-running instance on 8080): ran an IR comparison
  (`nfcorpus-20260619T200023Z` vs `nfcorpus-20260623T002234Z`), clicked "Judgement" on
  `PLAIN-2`, confirmed the qrels table matched a direct `curl` of
  `/api/eval/judgement?dataset=nfcorpus&queryId=PLAIN-2`, and confirmed clicking the row itself
  opened the content-expansion accordion (source lists) *underneath* the still-open Judgement
  panel — both visible at once. Also clicked a `doc_id` inside that expansion to confirm the
  Session-3 doc-fetch feature still works alongside the new panel. Confirmed
  `/api/eval/judgement?dataset=does-not-exist&queryId=PLAIN-2` → 404 and
  `?dataset=nfcorpus&queryId=does-not-exist` → 200 with an empty list, via direct `curl`. Ran a
  RAG comparison and confirmed the Judgement panel shows `ground_truth` ("(none)" for a row
  with no ground truth) with no additional network request, and that the row's expanded
  Answer/Contexts columns no longer show a Ground Truth section. Clicked through all other tabs
  (RAG, Query, Ingest, Eval, Metrics) and checked the console — no errors.
- `docs/wiki.md` updated: §4.6 gained a step 11 describing the Judgement panel (qrels for IR,
  `ground_truth` for RAG, independence from the content-expansion accordion, and the removal of
  the duplicated `ground_truth` from RAG's expanded columns); `GET /api/eval/compare`'s RAG
  response docs note the new `ground_truth`/`ground_truth_mismatch` fields; a new
  `GET /api/eval/judgement` reference entry was added alongside `GET /api/eval/document`.

**Deviations from plan (with rationale):** none — followed Plan.md §9.1–9.3 as specified.

---

## Session 5 — Run Comparison Amendment 4: Real OpenSearch Match Highlighting (2026-07-14)

**Model:** Claude Sonnet 5
**Branch:** 2026-07-11-run-comparison

**Prompt summary:**
> Implement not-completed tasks from `specs/2026-07-11-run-comparison/`, acting as a Python
> coach while making the changes, and asking clarifying questions via AskUserQuestion instead
> of assuming. Re-read `requirements.md`/`Plan.md`/`Validation.md` and the current state of
> `compare.py`/`routes.py`/`html.py`/`test_compare.py`; confirmed Groups 1–10 (base Compare tab
> through Amendment 3's clickable qrels `doc_id`) were already implemented and passing, and
> Group 11 (Amendment 4, F17/F18 — real OpenSearch match highlighting) was the only gap. Asked
> and confirmed scope (Group 11 only) and coaching style (inline explanations as I go) via
> `AskUserQuestion` before starting. Mid-implementation, the user asked to make sure `search()`
> and the new `highlight_document()` use the same query string construction; asked a follow-up
> `AskUserQuestion` and confirmed extracting a shared `_chunk_text_match()` helper.

**Outcome:**
- `search/bm25_searcher.py`: added `_chunk_text_match(text)` — the one place a `chunk_text`
  `match` clause is built — and refactored `search()` to use it. Added
  `highlight_document(client, query, doc_id, index)`: a `bool` query with `filter`/`term` on
  `_id` (returns the doc, non-scoring, if present at all) plus `should` +
  `minimum_should_match: 0` on `_chunk_text_match(query)` (only contributes
  scoring/highlighting, never excludes the hit) and a `highlight` block on `chunk_text`. Zero
  hits → `FileNotFoundError`; one hit with no `highlight` block → `[]` (valid "no match"
  outcome, not an error).
- `web/routes.py`: new `GET /api/eval/highlight?dataset=&docId=&query=` — same `..`/`/`
  validation as the other eval routes, plus a non-empty `query` check. Resolves the index via
  the existing `_resolve_index()`, catches `FileNotFoundError` → 404, and catches any other
  OpenSearch client exception broadly → `{"error": ...}` at `200`, mirroring `/api/query`'s
  existing convention (a live cluster call can fail for reasons unrelated to the doc/dataset).
- `web/html.py`: added `cmpHighlightCache` (keyed `dataset::docId::query`, unlike the plain
  `cmpDocCache` which has no query in its key). Refactored `toggleCompareDoc` into
  `fetchCompareDocument` + `fetchCompareHighlight` helpers run concurrently via `Promise.all`;
  the highlight fetch only fires when `cmpType === 'ir'` and the row has a `query_text`. Added
  `renderHighlightFragments()`, called from both `renderSourceList` (source-list expansion) and
  `renderJudgementPanel` (qrels `doc_id` expansion) so both entry points show the same
  highlighting without duplicate wiring. Fragments are escaped with the existing `esc()` helper
  first, then only the literal `&lt;em&gt;`/`&lt;/em&gt;` markers OpenSearch inserts are
  restored to real `<em>` tags — no raw `innerHTML` of unescaped document content.
- New `tests/test_bm25_searcher.py` (3 tests, using a hand-written `_FakeClient` stub rather
  than `unittest.mock.Mock`, so a typo in the expected call shape fails loudly instead of being
  silently accepted): fragments returned on a real hit, `[]` on a hit with no highlight block,
  `FileNotFoundError` on zero hits. Full suite (36 tests) passes.
- Verified end-to-end: restarted the locally running `searchlab serve` (an older process on
  port 8080 predated these changes and had no `/api/eval/highlight` route — confirmed via
  `AskUserQuestion` before killing it) against a live OpenSearch. Direct `curl` of
  `/api/eval/highlight?dataset=nfcorpus&docId=MED-14&query=...` returned real `<em>`-wrapped
  fragments matching qrels-relevant content; a nonexistent `doc_id` → 404; an unrelated query
  string against a real doc → `200` with `fragments: []`; a path-traversal `dataset` → 400. In
  a real Chrome tab, expanded an IR comparison row's source list, clicked `MED-14`, and
  confirmed highlighted fragments rendered above the plain title/text with real `<em>` DOM
  elements (`document.querySelectorAll('#cmp-tbody em')` returned 16 matches). Switched to a
  RAG comparison, expanded a row's content and its Judgement panel, and confirmed via
  `cmpHighlightCache` that no new entry was added — the only cache entry was the one from the
  earlier IR click — so no highlight request is ever fired for RAG rows.
- `docs/wiki.md` updated: §4.6 gained item 12 (highlighting: what's fetched, when, the
  live-index caveat, the shared `_chunk_text_match()` note, RAG's non-applicability); a new
  `GET /api/eval/highlight` reference entry alongside `/api/eval/document`/`/api/eval/judgement`;
  §3.4's key-symbols table and query-pattern note updated for `highlight_document` and
  `_chunk_text_match`; §3.6's key-symbols table notes the new route.

**Deviations from plan (with rationale):** Plan.md §11.1 didn't specify sharing the `match`
clause between `search()` and `highlight_document()` — it showed the highlight query body
inline with its own literal `{"match": {"chunk_text": query}}`. Per the user's explicit request
mid-session, extracted `_chunk_text_match()` as a shared helper instead, so the two functions
can't independently drift into scoring/highlighting documents differently if one is edited
later. No other deviation from Plan.md §11.1–11.3 / Requirements F17–F18.

---

## Session 6 — Index Management (2026-07-14)

**Model:** Claude Sonnet 5
**Branch:** 2026-07-14-index-management

**Prompt summary:**
> Implement the remaining task groups in `specs/2026-07-14-index-management/` (requirements.md,
> Plan.md, Validation.md). Nothing from this spec had been started yet, so all 8 plan groups were
> "remaining": a new Indexes tab to view every `searchlab-*` index with a live doc count and
> create a new one from an uploaded raw OpenSearch schema JSON, plus wiring newly-created indexes
> into the RAG/Query/Ingest dataset dropdowns via a new `GET /api/datasets` endpoint.

**Outcome:**
- New `opensearch/index_registry.py`: file-backed registry at
  `service/searchlab/data/index_registry.json` (git-ignored, created lazily). `load_registry`
  returns `[]` if missing; `save_entry` appends and writes via a temp-file + `os.replace` swap to
  avoid a torn file; `find_by_key`/`find_by_index`/`key_exists` lookups.
- New `opensearch/index_admin.py`: `validate_key` (lowercase/digits/hyphens, 1–63 chars, rejects
  `default`/`nfcorpus`/`fiqa` as reserved so a custom index can't shadow a built-in dataset);
  `create_index` (validates, rejects a name that already exists in OpenSearch or the registry,
  calls `indices.create()` with the uploaded body verbatim, does **not** write the registry entry
  itself — that's the route's job, only after `create_index` returns); `list_indexes` (one
  `cat.indices("searchlab-*")` call merged with registry metadata, `pre-existing`/`None` for
  indexes with no registry entry).
- `web/routes.py`: `GET /api/indexes` (502 on cluster failure), `POST /api/indexes` (multipart
  `name` + `schemaFile`; distinct 400s for invalid JSON, invalid name, and OpenSearch mapping
  rejection — the registry entry is written only after `create_index` succeeds), `GET
  /api/datasets` (merges the hardcoded BEIR entries with every registry entry). Extended
  `_resolve_index` to check the registry (`find_by_key`) between the hardcoded `DATASET_INDEX`
  dict and the default-index fallback. `POST /api/ingest` gained a `dataset` form field, resolved
  through `_resolve_index` instead of always targeting `config.index_name()`.
- `web/html.py`: new **Indexes** tab (create-index form + existing-indexes table, refresh
  button), added to the tab bar after Compare. New Ingest-tab dataset `<select>` defaulting to
  "Default index" (preserves pre-change behavior), wired into `runIngest()`'s POST body.
  `loadIndexes()`/`createIndex()`/`loadDatasets()`/`populateDatasetSelect()` — the last preserves
  each dropdown's current selection across a refresh (reads `select.value` before replacing
  `<option>`s, restores it after if still present) so creating an index elsewhere doesn't reset a
  user's in-progress RAG/Query/Ingest selection. `loadDatasets()` runs once at page load and again
  after a successful `createIndex()`.
- New `tests/test_index_registry.py`, `tests/test_index_admin.py` (hand-written `_FakeClient`
  stub with `.indices`/`.cat` sub-objects, same convention as `test_bm25_searcher.py`'s
  `_FakeClient` — not `unittest.mock.Mock`), `tests/test_routes.py` (`_resolve_index` precedence:
  hardcoded dict wins over registry, registry key resolves, unknown dataset falls back to
  default, unchanged).
- Fixed a pre-existing, unrelated `IndentationError` in `search/bm25_searcher.py:28` (present
  since the "Comparison feature" commit, predating this session) that broke every test's
  collection; confirmed with the user via `AskUserQuestion` before fixing it, since the whole
  suite couldn't otherwise run to verify this session's changes.
- Full suite: 60 passed (36 pre-existing + 24 new).
- Verified end-to-end against a live OpenSearch: an older `searchlab serve` process on port 8080
  predated these changes (no new routes) — confirmed via `AskUserQuestion` before killing it and
  starting a fresh one. `curl`-drove `GET /api/indexes`/`GET /api/datasets` (listed
  `searchlab-v0`/`-nfcorpus`/`-fiqa` as `pre-existing`), `POST /api/indexes` success + duplicate
  name/key rejection + invalid JSON + OpenSearch-rejected mapping + invalid name (all distinct
  400 messages, no stack traces), `POST /api/ingest` with `dataset=my-test-idx` (chunks landed in
  `searchlab-my-test-idx`, doc count rose, `searchlab-v0` untouched) and with no `dataset`
  (unchanged default-index behavior), `POST /api/query` against the new custom index. In a real
  Chrome tab: Indexes tab renders the create form and table correctly; RAG/Query/Ingest dataset
  dropdowns include the newly-created `my-test-idx` while Eval/Metrics/Compare dropdowns remain
  BEIR-only (`nfcorpus`/`FiQA-2018`/run lists) with no leakage; submitting the create form with no
  file selected shows the client-side inline error before any network call. Deleted the test
  index (`searchlab-my-test-idx`) and cleared the local registry file afterward.
- `docs/wiki.md` updated: repository structure and directory-purpose table note
  `opensearch/index_admin.py`/`index_registry.py` and the new `service/searchlab/data/` dir; §3.3
  documents the new index-admin/registry functions; §3.6's key-symbols table gains
  `_resolve_index` and the three new routes; new §4.7 "Index Management (Indexes tab)" workflow
  section (view/create flow, naming convention, the fixed-ingest-shape caveat, and why
  Eval/Metrics/Compare are structurally out of reach); §7 gained `GET/POST /api/indexes` and `GET
  /api/datasets` entries and updated `/api/ingest`'s entry for the new `dataset` field; §9's
  Dataset Index Mapping section rewritten around `_resolve_index`'s actual 4-step precedence;
  §10's service test-file table brought up to date (it was already missing
  `test_bm25_searcher.py`/`test_compare.py` from a prior session, plus the three new files added
  here).
- `.gitignore`: added `service/searchlab/data/` alongside the existing `searchlab-eval/results`
  entry, so the registry file is never committed.

**Deviations from plan (with rationale):** None from Plan.md's 8 groups. One out-of-scope fix
(the pre-existing `bm25_searcher.py` indentation bug) was made only after explicit user
confirmation, since it blocked all test collection and wasn't otherwise part of this spec.

---

## Session 7 — Index Management Amendment: Eval Ingest/Query Index Override (Group 9) (2026-07-16)

**Model:** Claude Sonnet 5
**Branch:** 2026-07-14-index-management

**Prompt summary:**
> Implement the remaining task groups in `specs/2026-07-14-index-management/`. Groups 1–8
> (Session 6) were already done; the spec had since grown a 9th group — an independent index-target
> override for the Eval tab's Ingest/Query steps, plus AC18–AC22 and manual-verification step 12 —
> that hadn't been implemented yet.

**Outcome:**
- `web/routes.py`: `/api/query` gained an `index` form field; when non-empty it's used verbatim
  and `_resolve_index(dataset)` is skipped entirely. `_build_eval_command` gained an `index`
  parameter, appending `--index <index>` to the `ingest`/`query` subcommands only when non-empty
  (`download`/`metrics`/`ragas` untouched). `/api/eval/stream` gained an `index` query param
  passed through to `_build_eval_command`.
- `searchlab-eval/searchlab_eval/cli.py`: `ingest` and `query` commands each gained `--index`
  (default `None`); when given, used verbatim instead of `f"searchlab-{dataset}"`; when omitted,
  byte-for-byte the same as before.
- `searchlab-eval/searchlab_eval/querier.py`: `run_query`/`run_queries` gained an `index` param;
  when set, POSTs `index=<index>` (and empty `dataset`) to `/api/query` instead of `dataset`;
  when `None`, POSTs `dataset` exactly as before.
- `web/html.py`: new `<select id="eval-index">` next to the Eval tab's dataset dropdown,
  first option "Default for dataset" (no override). `loadEvalIndexOptions()` populates it from
  `GET /api/indexes` on switching to the Eval tab and after a successful `createIndex()`.
  `runEvalOp()` appends `&index=<index>` to the `/api/eval/stream` URL for `ingest`/`query` only
  when the selector is non-blank.
- Tests: `test_routes.py` gained `_build_eval_command` index-append tests (ingest/query only;
  download/metrics/ragas unaffected) and `/api/query` tests (explicit `index` bypasses
  `_resolve_index`; empty `index` preserves dataset-based resolution) run via `asyncio.run()`
  against the route coroutine directly, since no route in this codebase was previously tested via
  `TestClient`/`pytest-asyncio`. `test_query.py` gained index-override coverage for
  `run_query`/`run_queries`; its pre-existing `test_run_queries_continues_on_error` fake needed an
  `index=None` kwarg added to keep matching `run_query`'s new signature. New `test_cli.py`
  (`click.testing.CliRunner`, first CLI test file in `searchlab-eval/tests/`) covers `ingest
  --index`/`query --index` vs. the default dataset-derived path, mocking `ingest_corpus`/
  `run_queries` since no import in `cli.py` is patchable at module load time (both are imported
  inside the command function body).
- Full suite: `service` 68 passed, `searchlab-eval` 31 passed (`-m "not integration"`).
- Verified end-to-end against a live OpenSearch: an older `searchlab serve` process on port 8080
  predated this session's routes.py changes — confirmed via `AskUserQuestion` before killing it
  and starting a fresh one. Created a custom index via `POST /api/indexes`, ran `searchlab-eval
  ingest --dataset nfcorpus --index <custom>` (3633 docs landed in the custom index,
  `searchlab-nfcorpus` unaffected), `searchlab-eval query --index <custom>` (323 queries →
  `raw_results.json`), `searchlab-eval metrics ir` against that run (scored normally — nDCG/MAP/
  Recall reported, matching is by `doc_id` against local qrels regardless of index), a direct
  `curl POST /api/query` with `index=<custom>` (response's `index` field matched), and confirmed
  the `#eval-index` selector is present in the served HTML. Re-ran `ingest`/`query` with `--index`
  omitted and confirmed the corpus landed back in `searchlab-nfcorpus` (AC21). Deleted the test
  index and its `raw_results.json`/registry entry afterward.
- `docs/wiki.md` updated: §4.4 gained an "Index-target override" subsection describing the
  Eval tab's new selector and how it threads through `runEvalOp` → `/api/eval/stream` →
  `_build_eval_command` → `cli.py --index` → `querier.py`; §4.7 cross-references it; `POST
  /api/query` and `GET /api/eval/stream` route docs (§7) document the new `index` parameter;
  §10's service and eval test-file tables updated for the new/changed test coverage.
- `Plan.md`'s Definition of Done and `Validation.md`'s Merge Checklist (AC1–AC22, manual steps
  1–12) marked complete.

**Deviations from plan (with rationale):** None. `querier.py`'s `run_query` sends both `index`
and `dataset` fields on every call (empty string for whichever is not in effect) rather than
conditionally omitting one — functionally identical to the spec's "instead of" wording since
`api_query` treats an empty `index` as absent, and simpler than building the request body
conditionally.

## Session 8 — Custom Run Name (2026-07-16)

**Model:** Claude Sonnet 5
**Branch:** 2026-07-16-custom-run-name

**Prompt summary:**
> Implement the remaining task groups in `specs/2026-07-16-custom-run-name/`. All 5 groups were
> unimplemented at session start (`--run-id` already existed as a CLI flag on `query`/`ragas` but
> was unused by the web UI/route layer).

**Outcome:**
- `searchlab-eval/searchlab_eval/cli.py`: new `_reject_if_run_exists(run_id)` helper (path-traversal
  chars rejected, then checks `results/<run_id>` existence) called from `query` and `ragas_cmd`
  only when `--run-id` was explicitly supplied by the caller — the auto-generated
  `{dataset}-{timestamp}` / `{dataset}-ragas-{timestamp}` path is never subject to the check, so
  omitted-flag behavior is byte-for-byte unchanged.
- `service/searchlab/web/routes.py`: `_build_eval_command`'s `"query"` and `"ragas"` branches
  append `--run-id <run_id>` when non-empty, mirroring the existing `index` handling in the same
  function; `"download"`/`"ingest"` remain unaffected by `run_id`.
- `service/searchlab/web/html.py`: `#eval-run-id` field relabeled "Run Name" (was "Run ID (for
  Metrics)") with an updated placeholder/title clarifying it's optional for Query/RAG Eval;
  `runEvalOp()` now sends `&runId=<value>` for `query`/`ragas` when non-blank, in addition to its
  existing unconditional send for `metrics`.
- Tests: `test_cli.py` gained 6 new cases (3 each for `query`/`ragas`) — collision rejected with
  the mocked run function never called, a new name succeeds and writes into `results/<name>/`, and
  an unrelated pre-existing `results/` entry doesn't trip the guard on the auto-generated path;
  ragas cases mock `searchlab_eval.rag_eval.generate`/`score` directly (module-level functions, no
  existing ragas CLI test to follow, so this establishes the pattern). `test_routes.py` gained 6
  `_build_eval_command` cases mirroring the existing index-override tests' style: append-when-given
  and omit-when-blank for `query`/`ragas`, plus `ingest`/`download` unaffected-by-`run_id` checks.
- Full suite: `searchlab-eval` 41 passed, `service` 76 passed.
- Not done this session: manual end-to-end verification against a live `searchlab serve` +
  OpenSearch (Validation.md steps 1–8) — no live service was started in this session, so those
  steps are unverified beyond the automated test suite and code inspection. Flagged to the user.
- `docs/wiki.md` §4.4 gained a "Custom run naming" paragraph describing the Run Name field's dual
  role and the collision-is-a-hard-error behavior.

**Deviations from plan (with rationale):** None.
