# Per-Query Run Comparison: Implementation Plan

> **Architecture decision:** All comparison logic lives behind one new read-only endpoint,
> `GET /api/eval/compare`, built on the JSON files the eval harness already writes
> (`ir_scores.json`, `rag_scores.json`, `rag_results.json`, `raw_results.json`). No new files
> are written to disk; no changes to `searchlab-eval`. The frontend gets one new tab
> (`Compare`) in the existing embedded HTML/JS shell (`service/searchlab/web/html.py`).

---

## Group 1 — Comparison Module (Backend)

**Where:** `service/searchlab/web/compare.py` (new file)

1.1 `load_ir_scores(run_id: str) -> dict` — reads `searchlab-eval/results/<run_id>/ir_scores.json`.
    Raises `FileNotFoundError` with a message naming the missing run if absent.

1.2 `load_rag_scores(run_id: str) -> dict` / `load_rag_results(run_id: str) -> dict` — same
    pattern for `rag_scores.json` / `rag_results.json`.

1.3 `load_raw_results(run_id: str) -> dict | None` — reads `raw_results.json` if present
    (`results` dict keyed by `query_id` → `[{doc_id, score, rank}, ...]`); returns `None` if
    missing (IR comparison still works, just without expandable content for that run).

1.4 `compare_ir(run_a: str, run_b: str) -> dict`:
    - Loads `ir_scores.json` for both; raises a `ValueError` (caught by the route, turned into
      a 400) if `dataset` fields differ.
    - Computes `measures` as the intersection of both runs' `measures` lists.
    - Builds `rows`: for every `query_id` present in **both** `per_query` dicts, emit
      `{query_id, a: {...metrics}, b: {...metrics}, delta: {...per measure b-a}}`.
    - Builds `only_in_a` / `only_in_b`: `query_id` lists present in one run's `per_query` but
      not the other's.
    - Attaches `sources_a` / `sources_b` per row from `load_raw_results`, if available, keyed
      by the same `query_id`.

1.5 `compare_rag(run_a: str, run_b: str) -> dict`:
    - Loads `rag_scores.json` (metrics, keyed `"0"`, `"1"`, … ) and `rag_results.json` (content,
      list-indexed) for both runs; raises `ValueError` on dataset mismatch.
    - `measures` = intersection of both runs' `measures`.
    - Iterates `range(min(len(results_a), len(results_b)))`; for each index `i` emits
      `{index: i, query_id: results_a[i]["query_id"], a: {...metrics}, b: {...metrics},
      delta: {...}, content_a: results_a[i], content_b: results_b[i]}`.
    - Indices beyond the shorter run's length go into `only_in_a` / `only_in_b` (using that
      run's own `query_id` at that position, plus its content), so nothing is silently dropped.

1.6 Both `compare_ir` and `compare_rag` return a dict shape close enough that the frontend can
    share one table-rendering function: `{run_a, run_b, dataset, measures, rows, only_in_a,
    only_in_b}`.

---

## Group 2 — Route

**Where:** `service/searchlab/web/routes.py`

2.1 Add `GET /api/eval/compare`:
    ```python
    @router.get("/api/eval/compare")
    async def eval_compare(
        type: str = Query(...),   # "ir" | "rag"
        runA: str = Query(...),
        runB: str = Query(...),
    ):
    ```
    - Validate `runA`/`runB` the same way existing endpoints do (`".." not in`, `"/" not in`).
    - Validate `type in {"ir", "rag"}`, else 400.
    - Call `compare_ir` or `compare_rag`; catch `FileNotFoundError` → 404 with the missing
      run/file named; catch `ValueError` (dataset mismatch) → 400 with both datasets named.
    - Return the dict as JSON.

2.2 Extend `/api/eval/runs` (already returns `hasMetrics` / `hasRagMetrics` per run) — no
    schema change needed; the Compare tab reuses this existing endpoint to populate its run
    dropdowns, filtering client-side on `hasMetrics` (IR) or `hasRagMetrics` (RAG) and on
    `dataset`.

---

## Group 3 — Compare Tab Shell

**Where:** `service/searchlab/web/html.py`

3.1 Add `Compare` to the tab bar (`RAG | Query | Ingest | Eval | Metrics | Compare`), same
    hash-routing pattern (`#compare`) as the other tabs.

3.2 Compare tab controls:
    - Type toggle: **IR** | **RAG**.
    - Dataset dropdown, populated from `/api/eval/runs` (distinct `dataset` values for runs
      matching the selected type).
    - Run A / Run B dropdowns, populated from `/api/eval/runs` filtered to the chosen dataset
      + type, sorted by `computedAt` descending.
    - "Compare" button → `GET /api/eval/compare?type=&runA=&runB=`.

---

## Group 4 — Comparison Table

**Where:** `service/searchlab/web/html.py` (JS in the embedded page)

4.1 Render `measures` as columns, each split into `A | B | Δ` sub-columns, plus a leading
    `Query` column (`query_id`).

4.2 Δ cells colored: green if improvement, red if regression, grey if `|delta| < 0.01` or a
    metric is missing on one side.

4.3 Default sort: ascending on `delta[primary_measure]` (`ndcg_cut_10` for IR, `faithfulness`
    for RAG) — worst regressions first. Column headers are clickable to re-sort, matching the
    existing Metrics tab sortable-table behavior.

4.4 "Only in Run A" / "Only in Run B" rendered as a separate, visibly distinct section below
    the main table (not interleaved), each row showing that run's own metric values only.

---

## Group 5 — Expandable Row Content

**Where:** `service/searchlab/web/html.py`

5.1 Clicking a row toggles an inline expansion showing content for A and B side by side:
    - **RAG rows:** `question` (shown once, shared), then two columns — Run A `answer` /
      `contexts` / `ground_truth`, Run B `answer` / `contexts` / `ground_truth`.
    - **IR rows:** two columns of ranked source lists (`doc_id`, `score`, `rank`) from
      `sources_a` / `sources_b`; if `raw_results.json` was unavailable for a run, show
      "No source detail for this run" instead of leaving the column blank.

5.2 Only one row expanded at a time (accordion), to keep the table usable at 50+ rows.

---

## Group 6 — Error States

**Where:** `service/searchlab/web/html.py`, `routes.py`

6.1 Backend errors (missing run, dataset mismatch, bad `type`) surface as a red banner with
    the exact message from the API — same pattern as the existing Eval tab's error banner.

6.2 Empty comparison (zero shared rows, e.g. two runs with disjoint query sets) shows an
    explicit "No overlapping queries between these two runs" message instead of an empty table,
    with the only-in-A/only-in-B section still populated below it.

---

## Group 7 — Documentation

**Where:** `docs/wiki.md`

7.1 Document the Compare tab: how to reach it, that it requires two runs of the same type and
    dataset, and what the Δ convention means (`B - A`, green = improvement).

7.2 Note the RAG positional-join caveat: comparing two RAG runs with different `--slice` sizes
    only compares the overlapping prefix.

---

## Group 8 — Amendment: Metric Filter, Query Text, Document Fetch (2026-07-11)

Extends Group 4 (table columns) and Group 5 (row expansion). No changes to Groups 1–7's
endpoint contracts other than the additive fields listed below.

### 8.1 Metric filter dropdown

**Where:** `service/searchlab/web/html.py` (JS)

- Add a `<select>` next to the type/dataset/run pickers (Group 3.2), populated from the
  comparison response's `measures` list plus a leading "All metrics" option, disabled until a
  comparison has been run.
- On change, re-render the existing table/only-in-A/only-in-B DOM with a column subset
  (`Query` + the chosen metric's `A`/`B`/`Δ`) instead of all measures. Row data and row order
  are untouched — this is a render-time column filter, not a re-fetch or a re-sort.
- Default (`All metrics`) reproduces exactly the Group 4 behavior already implemented.

### 8.2 Query text

**Where:** `service/searchlab/web/compare.py`, `service/searchlab/web/html.py`

- `compare.py`: add `_load_queries(dataset: str) -> dict[str, str]` — reads
  `searchlab-eval/data/<dataset>/queries.jsonl` line by line (`{"_id", "text"}`), returns
  `{}` if the file is missing (caught, not raised — a missing queries file degrades to
  `query_id`-only display, it doesn't fail the comparison).
- `compare_ir`: attach `query_text: queries.get(qid)` to every entry in `rows`, `only_in_a`,
  `only_in_b`.
- `compare_rag`: attach `query_text: results_a[i].get("question")` to each `rows` entry (and
  the analogous own-run field to `only_in_a`/`only_in_b` entries). If
  `results_a[i]["question"] != results_b[i]["question"]`, also attach
  `query_text_mismatch: True` so the UI can flag it instead of silently picking Run A's text.
- `html.py`: render `query_text` in the table's `Query` column (falling back to `query_id` alone
  when `query_text` is `null`); render a warning marker on rows where `query_text_mismatch` is
  set, matching the existing error-banner visual language (Group 6).

### 8.3 Document fetch on doc_id click

**Where:** `service/searchlab/web/compare.py`, `service/searchlab/web/routes.py`,
`service/searchlab/web/html.py`

- `compare.py`: add `load_document(dataset: str, doc_id: str) -> dict` — reads
  `searchlab-eval/data/<dataset>/corpus.jsonl` line by line looking for a matching `_id`
  (small/medium BEIR corpora; no indexing needed for this scale). Raises `FileNotFoundError`
  if the dataset directory or `corpus.jsonl` is missing, or if no line matches `doc_id`.
- `routes.py`: add `GET /api/eval/document?dataset=&docId=`, validating both params the same
  way `runA`/`runB` are validated (reject `..`/`/`), catching `FileNotFoundError` → 404.
- `html.py`: in the IR row expansion's source list (Group 5.1), make each `doc_id` entry
  clickable; on click, `fetch` the new endpoint and toggle an inline block under that entry
  showing `title` + `text` (collapse on second click). Cache responses client-side keyed by
  `(dataset, doc_id)` for the session to avoid redundant fetches. Show a lightweight inline
  "loading…" state and, on 404, an inline "Document not found" message rather than blocking the
  whole row.

---

## Group 9 — Amendment 2: Judgement Panel (2026-07-11)

Extends Group 4 (main table row) and modifies Group 5.1 (RAG expanded content). Adds one new
endpoint, mirroring the doc_id fetch-on-click pattern from Group 8.3.

### 9.1 IR: qrels loader and endpoint

**Where:** `service/searchlab/web/compare.py`, `service/searchlab/web/routes.py`

- `compare.py`: add `load_qrels(dataset: str, query_id: str) -> list[dict]` — reads
  `searchlab-eval/data/<dataset>/qrels/test.tsv` (BEIR TSV: `query-id`, `corpus-id`, `score`,
  header row), filters to rows matching `query_id`, returns `[{doc_id, score}, ...]`. Raises
  `FileNotFoundError` if the dataset directory or `qrels/test.tsv` is missing. Returns `[]`
  (not an error) if the file exists but no row matches `query_id` — a query with zero judged
  docs is a valid data state.
- `routes.py`: add `GET /api/eval/judgement?dataset=&queryId=`, validating both params the same
  way `runA`/`runB`/`docId` are validated (reject `..`/`/`). Catches `FileNotFoundError` → 404.
  Returns `{query_id, judgements: [...]}` (200, possibly empty list).

### 9.2 RAG: ground_truth promoted to row-level, deduplicated

**Where:** `service/searchlab/web/compare.py`

- `compare_rag`: add `ground_truth: results_a[i].get("ground_truth")` to each `rows` entry
  (mirrors the `query_text` attachment in Group 8.2). Add `ground_truth_mismatch: True` if
  `results_a[i].get("ground_truth") != results_b[i].get("ground_truth")`, same pattern as
  `query_text_mismatch`.
- Remove `ground_truth` from `content_a` / `content_b` as consumed by the row-expansion
  rendering (Group 5.1) — the raw dict from `rag_results.json` still contains it, but the
  frontend's Run A / Run B expanded columns now render `answer` / `contexts` only; `ground_truth`
  is rendered once, from the row-level field, inside the Judgement panel (9.3).

### 9.3 Judgement link and panel

**Where:** `service/searchlab/web/html.py` (JS)

- In the main table row (Group 4.1), add a "Judgement" link/button in the Query column, next to
  `query_text` — for both IR and RAG rows, always visible (not gated behind row expansion).
- Click toggles an inline panel directly under that row. This toggle is independent of the
  row's content-expansion accordion (Group 5.2's "only one expanded at a time" rule applies only
  to that accordion, not to Judgement panels — multiple Judgement panels may be open
  simultaneously, same as doc_id inline expansions within a row are independent of each other).
- **IR:** on first open, `fetch('/api/eval/judgement?dataset=&queryId=')`, cache client-side
  per `(dataset, query_id)` for the session (same convention as the doc_id cache from Group
  8.3). Render `doc_id | score` pairs. Empty list → "No judgements recorded for this query."
  404 → inline "Judgements unavailable for this dataset" (not a blocking error).
- **RAG:** no fetch — render the row's `ground_truth` field (already present in the compare
  response) directly. If `ground_truth_mismatch` is set, show both runs' ground_truth values
  with a warning marker, matching the `query_text_mismatch` visual treatment (Group 8.2).

---

## Group 10 — Amendment 3: Clickable `doc_id` in the IR Judgement Panel (2026-07-11)

Extends Group 9.3 (Judgement panel). No backend changes — this reuses `GET /api/eval/document`
(Group 8.3) and its existing client-side cache as-is.

### 10.1 Wire doc_id clicks in the Judgement panel to the existing document fetch

**Where:** `service/searchlab/web/html.py` (JS)

- In the IR Judgement panel's rendering (Group 9.3), make each `doc_id` entry in the
  `judgements` list clickable using the same handler/renderer already built for source-list
  `doc_id` clicks (Group 8.3) — not a second implementation.
- Reuse the existing client-side cache keyed by `(dataset, doc_id)` from Group 8.3 so a document
  fetched from either the source list or the Judgement panel is not re-fetched from the other.
- Toggling shows/hides an inline `title` + `text` block directly under the clicked judgement
  entry; independent of other doc_id expansions in the same panel (multiple can be open at once)
  and independent of the row's content-expansion accordion (Group 5.2), same as Group 9.1's
  panel-toggle independence.
- Same inline "loading…" / 404 "Document not found" states as Group 8.3.

---

## Group 11 — Amendment 4: Real OpenSearch Match Highlighting (2026-07-14)

Extends Group 8.3 (document fetch on doc_id click) and Group 10 (Judgement panel doc_id click),
which already share one expansion handler in the frontend. IR only. No changes to `compare.py`'s
existing functions or to `/api/eval/compare`'s response shape.

### 11.1 Highlight search function

**Where:** `service/searchlab/search/bm25_searcher.py`

- Add `highlight_document(client, query: str, doc_id: str, index: str) -> list[str]`, mirroring
  the existing `search()` function's client-call style. Query body:
  ```python
  {
      "query": {
          "bool": {
              "filter": [{"term": {"_id": doc_id}}],
              "should": [{"match": {"chunk_text": query}}],
              "minimum_should_match": 0,
          }
      },
      "highlight": {"fields": {"chunk_text": {}}},
      "size": 1,
  }
  ```
  The `filter`/`term` on `_id` guarantees the doc is returned (non-scoring) if it exists in the
  index at all, regardless of whether `query`'s terms match; `should` + `minimum_should_match: 0`
  means the `match` clause only contributes to scoring/highlighting, never excludes the hit. This
  is what lets the function distinguish "doc not in the live index" (zero hits → 404) from "doc
  exists but nothing matched" (one hit, empty/absent `highlight` block → `200` with `[]`).
- Returns `resp["hits"]["hits"][0].get("highlight", {}).get("chunk_text", [])` if `hits` is
  non-empty, else raises `FileNotFoundError` (doc not in live index) — same exception convention
  `compare.py`'s loaders already use, so the route layer's existing `except FileNotFoundError`
  pattern needs no new branch.

### 11.2 Route

**Where:** `service/searchlab/web/routes.py`

- Add `GET /api/eval/highlight`:
  ```python
  @router.get("/api/eval/highlight")
  async def eval_highlight(dataset: str = Query(""), docId: str = Query(""), query: str = Query("")):
  ```
  - Validate `dataset`/`docId` the same way `/api/eval/document` does (reject empty, `..`, `/`).
    `query` is validated non-empty only (free text, no path semantics).
  - Resolve the index via the existing `_resolve_index(dataset)` (already used by `/api/query`,
    `/rag`) and create a client via the existing `create_client()` — both already imported in
    this module, no new plumbing.
  - Call `highlight_document(client, query, docId, index)`; catch `FileNotFoundError` → 404;
    catch other OpenSearch client exceptions the same way `/api/query` does (broad `except
    Exception` → `{"error": str(e)}`, since a live cluster call can fail for reasons unrelated to
    the doc/dataset — connection errors, mapping errors — and those must not surface as a stack
    trace either).
  - Return `{"doc_id": docId, "fragments": fragments}` (200; `fragments` may be `[]`).

### 11.3 Frontend wiring

**Where:** `service/searchlab/web/html.py`

- Add `const cmpHighlightCache = new Map();` alongside the existing `cmpDocCache` (line ~437).
  Cache key is `` `${dataset}::${docId}::${query}` `` — unlike the plain document cache, the
  highlight result depends on which query produced it, so the key must include it.
- In `toggleCompareDoc` (currently `html.py:1231`), after expanding (`cmpExpandedDocs.add(key)`)
  and gated on `cmpType === 'ir'`: look up the row's `query_text` the same way `toggleJudgement`
  already does (`cmpData.rows.find(r => String(rowKey(r)) === rowKeyStr)` — both the source-list
  and Judgement-panel call sites pass a row-scoped `rowKeyStr`, so this lookup works for both
  without new parameters threaded through `renderSourceList`/`renderJudgementPanel`). Fire
  `fetch('/api/eval/highlight?dataset=...&docId=...&query=...')` alongside the existing
  `/api/eval/document` fetch (both can run concurrently; independent cache entries, independent
  loading states).
- In the detail-row rendering shared by `renderSourceList` (`html.py:1219-1222`) and
  `renderJudgementPanel` (`html.py:1162-1165`), render the highlight fragments (if any) above the
  plain `text`. **Fragments must not be inserted via raw `innerHTML`** — the fragment text is
  OpenSearch's copy of the indexed `chunk_text`, i.e. ingested document/corpus content, not
  something this feature controls; blindly rendering it as HTML would let any markup already
  present in a source document execute in the page. Escape each fragment with the existing
  `esc()` helper first (same as every other doc/title render in this file), then restore only the
  literal `<em>`/`</em>` markers OpenSearch inserts — e.g.
  `esc(fragment).replaceAll('&lt;em&gt;', '<em>').replaceAll('&lt;/em&gt;', '</em>')` — so the
  emphasis markup survives while everything else stays escaped. Empty `fragments` renders "No
  live-index match for this query" instead of an empty block. A `cmpHighlightCache` entry with
  `status: 'error'` renders inline, same visual pattern as the existing doc-fetch error state —
  never blocks the plain `title`/`text` block, which renders independently from its own
  `cmpDocCache` entry.

---

## Group 12 — Amendment 5: Judgement/Retrieved Cross-Reference Highlighting (2026-07-14)

Extends Group 9.3's Judgement panel and the source-list rendering added alongside it. No backend
changes — reuses `GET /api/eval/judgement` (Group 9.1) and its existing client-side cache, and the
`sources_a`/`sources_b` fields already present in `/api/eval/compare`'s response (Group 1.4). IR
only. No changes to `compare.py` or `routes.py`.

### 12.1 Trigger qrels fetch on row expansion, not just on Judgement-panel open

**Where:** `service/searchlab/web/html.py`, `toggleCompareRow` (currently line 1010)

- Currently `toggleCompareRow` only flips `cmpExpandedKey` and re-renders; the qrels fetch is
  only triggered from `toggleJudgement` (line 1091). Add: when expanding (not collapsing) an IR
  row, look up `cmpJudgementCache.get(`${dataset}::${row.query_id}`)`; if absent, kick off the
  same fetch-and-cache logic already in `toggleJudgement` (lines 1101–1119) — factor that block
  into a shared `ensureJudgementLoaded(row)` helper called from both `toggleJudgement` and
  `toggleCompareRow`, so there is one fetch/cache implementation, not two.
- This fetch runs in the background; `renderSourceList` renders without judged-status marks until
  it resolves, then re-renders with marks (same pattern as `fetchCompareHighlight` in
  `toggleCompareDoc`, lines 1244–1254).

### 12.2 Mark judged `doc_id`s in the source list

**Where:** `service/searchlab/web/html.py`, `renderSourceList` (currently line 1205)

- `renderSourceList` currently takes `(sources, rowKeyStr, side, queryText)`; add a `row` (or
  `queryId`) parameter so it can look up `cmpJudgementCache.get(`${dataset}::${row.query_id}`)`
  itself, mirroring how `renderHighlightFragments` looks up its own cache (line 1295).
- For each source entry, if the judgement cache has resolved (`status === 'ok'`) and
  `judgements` contains a matching `doc_id`, render a badge next to that row: distinguish
  score `> 0` ("Judged relevant") from score `=== 0` ("Judged non-relevant") with different
  styling (e.g. green vs. grey), consistent with the existing delta color convention
  (`deltaCls`, line ~999) rather than inventing a new color language.
- No badge (not "not judged" text) when the cache hasn't resolved yet or the `doc_id` isn't in
  the judgements list — keep the row visually identical to today's rendering in the no-match
  case, only additive when there is a match.

### 12.3 Mark retrieved `doc_id`s in the Judgement panel

**Where:** `service/searchlab/web/html.py`, `renderJudgementPanel` (currently line 1122, IR qrels
branch lines 1140–1176)

- For each qrels entry, check membership (and index/rank) in `row.sources_a` and `row.sources_b`
  (already available on `row`, no fetch). If found in either, render a badge showing which run(s)
  and at what rank, e.g. "Retrieved: A #3" / "Retrieved: B #7" / "Retrieved: A #2, B #5".
- No badge when the `doc_id` isn't present in either run's sources — same additive-only rule as
  12.2.

### 12.4 Shared lookup helper

**Where:** `service/searchlab/web/html.py`

- Add a small helper, e.g. `sourceRank(sources, docId)` returning the matching entry's `rank` or
  `null`, used by both 12.2 (checking `sources_a`/`sources_b` isn't needed there, only qrels
  lookup is) and 12.3 (checking rank in each side's sources) — avoids duplicating the `find`/
  `indexOf` logic in two render functions.

---

## Group 13 — Amendment 6: Aggregate Metrics Comparison & Improved/Regressed Filter (2026-07-16)

Extends Group 1 (backend response shape), Group 4 (comparison table), and Group 8.1 (metric
filter). No new endpoint — `aggregate` already exists in `ir_scores.json`/`rag_scores.json`
(Group 1.4/1.5 already load these files in full); this group only extracts and exposes it, plus
adds a client-side row filter alongside the existing metric-column filter.

### 13.1 Backend: aggregate delta

**Where:** `service/searchlab/web/compare.py`

- In `compare_ir` and `compare_rag`, after computing `measures` (the shared-measure
  intersection), extract `aggregate_a = _metric_subset(scores_a.get("aggregate", {}), measures)`
  and `aggregate_b = _metric_subset(scores_b.get("aggregate", {}), measures)` — reusing the
  existing `_metric_subset` helper (already used for per-row `a`/`b`). Compute
  `aggregate_delta = _delta(aggregate_a, aggregate_b, measures)`, reusing the existing `_delta`
  helper unchanged.
- Add `aggregate_a`, `aggregate_b`, `aggregate_delta` to the dict returned by both functions,
  alongside the existing `run_a`, `run_b`, `dataset`, `measures`, `rows`, `only_in_a`,
  `only_in_b` keys.

### 13.2 Frontend: aggregate summary block

**Where:** `service/searchlab/web/html.py`

- Add a summary block rendered above the per-query table once `cmpData` is populated: one row
  per shared measure showing `measure | A | B | Δ`, using the same `deltaCls` coloring helper
  already used for per-query Δ cells (Plan 4.2) so the color language is identical.
- Always renders **all** measures in `cmpData.measures`, independent of the per-query
  metric-column `<select>` (Group 8.1) — that control only narrows the per-query table's
  columns, not this block.
- Re-rendered whenever a new comparison response loads. Not affected by row sort or by the
  improved/regressed filter (13.3), since it summarizes the whole run pair, not a row subset.

### 13.3 Frontend: improved/regressed filter toggle

**Where:** `service/searchlab/web/html.py`

- Add a three-way toggle ("All" / "Improved in B" / "Regressed in B") next to the existing
  metric-column `<select>` (Group 8.1), disabled until a comparison has been run, defaulting to
  "All".
- Compute the "active filter metric" on each render: the metric-column dropdown's current value
  if it's not "All metrics", else the type's primary measure (`ndcg_cut_10` for IR,
  `faithfulness` for RAG — the same constant Group 4.3's default-sort logic already uses).
- Filtering predicate applied to the main table's row list before rendering (not a re-fetch, not
  a re-sort): for each row, read `row.delta[activeMetric]`.
  - Missing (metric not comparable for that row) → excluded from both "Improved in B" and
    "Regressed in B"; still shown under "All".
  - `> 0.01` → shown under "Improved in B".
  - `< -0.01` → shown under "Regressed in B".
  - Otherwise (grey zone) → excluded from both filtered views, same as "missing".
  - Reuse the existing grey-zone numeric constant from Group 4.2's delta-coloring logic rather
    than duplicating the literal `0.01` in a second place.
- Changing the metric-column dropdown while a non-"All" filter is active re-runs the filter
  against the newly active metric (no separate "apply" step).
- The only-in-A/only-in-B sections (Group 4.4) are unaffected by this toggle in every state —
  they render identically regardless of filter selection.

### 13.4 Definition of Done additions

See updated Definition of Done below.

---

## Group 14 — Amendment 7: Zero-Value Metric Counts (2026-07-17)

Extends Group 13's aggregate summary block. No new endpoint — reuses the `scores_a`/`scores_b`
`per_query` dicts that `compare_ir`/`compare_rag` already load in full (Group 1.4/1.5). This is a
per-run count, computed the same way `aggregate_a`/`aggregate_b` are: over that run's own
`per_query` dict, not just the rows shared with the other run — a run's zero-count is a property
of that run alone, so an `only_in_a`/`only_in_b` row still counts toward its own run's total.

### 14.1 Backend: per-run zero counts

**Where:** `service/searchlab/web/compare.py`

- Add `_zero_counts(per_query: dict, measures: list[str]) -> dict` — for each measure in
  `measures`, counts how many entries in `per_query` have that measure present and equal to `0`
  (`== 0`, not falsy/`None` — a missing metric for a query is not the same signal as a scored
  zero, so `None`/absent values are skipped, not counted).
- In `compare_ir`, call `_zero_counts(pq_a, measures)` / `_zero_counts(pq_b, measures)` right
  after `aggregate_delta` is computed (near line 135), producing `zero_counts_a` /
  `zero_counts_b`.
- In `compare_rag`, same call using `pq_a` / `pq_b` (near line 203) — these are already the full
  `rag_scores.json` `per_query` dicts (keyed `"0"`, `"1"`, …), so no change to how RAG's
  positional join works; the zero-count is independent of the A/B join.
- Add `zero_counts_a`, `zero_counts_b` to the dict returned by both functions, alongside the
  existing `aggregate_a` / `aggregate_b` / `aggregate_delta` keys (near lines 187–189 and
  264–266).

### 14.2 Frontend: zero-count columns in the aggregate summary block

**Where:** `service/searchlab/web/html.py`

- Extend the aggregate table header (`html.py:405`) with two more columns:
  `<th>Measure</th><th>A</th><th>B</th><th>Δ</th><th>Zero in A</th><th>Zero in B</th>`.
- In `renderCompareAggregate` (`html.py:1091`), append `zero_counts_a`/`zero_counts_b` lookups
  per measure and two more `<td>`s per row: plain counts, no color coding (a zero-count is not a
  delta, so `deltaCls`/`metricCls` don't apply — render as plain text, falling back to `0` if the
  measure key is absent from the dict).
- Same visibility rule as the rest of the aggregate block (Group 13.2): always shows all shared
  measures, unaffected by the per-query metric-column filter (`cmpMetricFilter`) or the
  improved/regressed row filter (`cmpRowFilter`) — this block summarizes the whole run pair, not
  a filtered row subset.

---

## Definition of Done

- [ ] `GET /api/eval/compare` works for both `type=ir` and `type=rag`
- [ ] Dataset/type mismatch produces a clear 400, not a crash or bad table
- [ ] Missing run produces a clear 404
- [ ] Compare tab renders run pickers filtered correctly by dataset + type
- [ ] Table shows A/B/Δ per measure, color-coded, default-sorted worst-regression-first
- [ ] Column headers re-sort the table
- [ ] Row expansion shows RAG content (question/answer/contexts/ground_truth) or IR content
      (ranked source lists) side by side
- [ ] Only-in-A / only-in-B section is visible and separate from the main table
- [ ] No changes to `searchlab-eval` output schemas or existing Metrics tab behavior
- [ ] Existing tests still pass; new unit tests cover `compare_ir` / `compare_rag` merge logic
- [ ] Metric dropdown narrows the table to one measure's A/B/Δ columns without changing sort order
- [ ] IR rows show real query text (from `queries.jsonl`) alongside `query_id`; missing
      `queries.jsonl` degrades gracefully instead of failing the comparison
- [ ] RAG rows show `question` text in the main table row, not just on expand; a mismatch
      between Run A's and Run B's question at the same position is flagged, not silently hidden
- [ ] Clicking a `doc_id` in an expanded IR row fetches and inlines that document's title/text
      via `GET /api/eval/document`; missing dataset/doc produces a clear inline error
- [ ] Every row shows a "Judgement" link next to the query text; clicking toggles an inline
      panel independent of the row's content-expansion accordion
- [ ] IR Judgement panel fetches qrels via `GET /api/eval/judgement` and shows `doc_id`/`score`
      pairs; empty judgements and missing qrels file both degrade gracefully (no crash)
- [ ] RAG Judgement panel shows `ground_truth` from the compare response with no extra fetch;
      a Run A/B `ground_truth` mismatch at the same position is flagged, not silently hidden;
      `ground_truth` no longer appears duplicated inside the per-run expanded content columns
- [ ] Clicking a `doc_id` inside the IR Judgement panel fetches and inlines that document's
      title/text, sharing the same cache as the source-list `doc_id` click (no duplicate fetch)
- [ ] Expanding an IR `doc_id` (source list or Judgement panel) also fetches and shows real
      OpenSearch match highlighting via `GET /api/eval/highlight`, without a separate user action
- [ ] Highlight fragments render with matched terms emphasized but all other content HTML-escaped
      — no raw `innerHTML` of unescaped document text
- [ ] Highlight fetch failures (doc missing from live index, no match, cluster error) degrade to
      an inline message and never block the plain document title/text already shown
- [ ] RAG rows are unaffected by this amendment — no highlight fetch, no new UI element
- [ ] Expanding an IR row's source list marks `doc_id`s also present in that query's qrels
      (judged relevant vs. judged non-relevant distinguished), triggering a background
      `/api/eval/judgement` fetch if not already cached — works whether the Judgement panel was
      opened first or not
- [ ] The IR Judgement panel marks each qrels `doc_id` also present in `sources_a`/`sources_b`
      with which run(s) retrieved it and at what rank, using data already on hand (no new fetch)
- [ ] No new endpoint or response-shape change for Amendment 5; RAG rows show no cross-reference
      marking
- [ ] `/api/eval/compare` includes `aggregate_a`/`aggregate_b`/`aggregate_delta` for both `type=ir`
      and `type=rag`, matching each run's own `aggregate` dict in `ir_scores.json`/`rag_scores.json`
- [ ] Compare tab shows an aggregate summary block above the per-query table, always showing all
      shared measures regardless of the per-query metric-column filter's selection
- [ ] "All / Improved in B / Regressed in B" toggle correctly filters main-table rows by the
      active metric's delta (metric-dropdown selection, or the type's primary measure when on
      "All metrics"), using the existing grey-zone threshold; only-in-A/only-in-B sections are
      unaffected in every filter state; switching the metric dropdown re-evaluates an active filter
- [ ] `/api/eval/compare` includes `zero_counts_a`/`zero_counts_b` for both `type=ir` and
      `type=rag`, counting each run's own `per_query` entries per shared measure equal to exactly
      `0` (missing/`None` values excluded, not counted as zero)
- [ ] Aggregate summary block shows "Zero in A" / "Zero in B" columns per measure alongside the
      existing A/B/Δ columns, unaffected by the metric-column filter and the improved/regressed
      row filter
