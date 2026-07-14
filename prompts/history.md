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
