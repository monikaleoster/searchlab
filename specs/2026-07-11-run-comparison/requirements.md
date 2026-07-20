# Per-Query Run Comparison: Requirements

## Context

The Metrics tab (`service/searchlab/web/routes.py`, `/api/eval/results`, `/api/eval/rag-results`)
already renders a single eval run's aggregate + per-query metrics — either an IR run
(`ir_scores.json`: nDCG/Recall/MAP) or a RAG/RAGAS run (`rag_scores.json`: faithfulness,
answer_relevancy, context_recall, context_precision). Today there is no way to see two runs
side by side. Per the Constitution's Measurement Principle (§II), every retrieval or RAG change
should produce a comparable number — but right now that comparison is done by eyeballing two
separate JSON files or Metrics-tab loads.

This work adds a per-query comparison between two runs of the same type, so a regression or
improvement can be traced down to the individual query that caused it, not just the aggregate.

Guidance reference (per user decision — `specs/mission.md`/`techstack.md` do not exist in this
repo): `CONSTITUTION.md` (mission/principles) and `README.md` (tech stack — Python 3.12,
FastAPI, embedded server-rendered HTML/JS UI, OpenSearch, `searchlab-eval` harness writing to
`searchlab-eval/results/<runId>/`).

---

## Objective

Let a user pick two existing runs of the **same type** (both IR eval runs, or both RAG/RAGAS
runs) from the same dataset, and see, per query:

- Each run's metric values and the delta between them.
- The underlying content that produced those numbers (question/answer/contexts for RAG;
  retrieved sources for IR), so a metric swing is explainable without opening raw JSON files.

This is read-only. No changes to how runs are produced (`searchlab-eval download/ingest/query/
ragas`), no changes to `ir_scores.json` / `rag_scores.json` / `rag_results.json` schemas.

---

## Scope Decisions

### Same type, same dataset only

Comparing an IR run against a RAG run is meaningless (disjoint metrics). Comparing across
datasets is meaningless at the per-query level (query IDs / questions don't correspond). The
Compare tab picks a dataset first, then two runs within that dataset that are both IR-eval runs
or both RAG-eval runs. Cross-type or cross-dataset run pairs are rejected by the backend with a
clear error, not silently mismatched.

### Row key differs by run type

| Run type | Source files | Row key | Content fields |
|---|---|---|---|
| IR | `ir_scores.json` | `query_id` (e.g. `PLAIN-2`) — already the `per_query` dict key | Retrieved hits from `raw_results.json` per query, if present |
| RAG | `rag_scores.json` + `rag_results.json` | list position (`rag_scores.json` `per_query` is keyed `"0"`, `"1"`, … — positional index into `rag_results.json`'s `per_query` list) | `question`, `answer`, `contexts`, `ground_truth` from `rag_results.json` at that index |

RAG comparison joins two runs by **position**, not `query_id`, because that's the only key
`rag_scores.json` has. This assumes both runs were sliced deterministically from the same
dataset ordering (true today — `slice_hf`/BEIR slicing takes the first N in a fixed order). If
run A and run B have different `--slice` sizes, only `min(lenA, lenB)` positions are compared;
extra rows in the longer run are shown in an "unmatched" section, not silently dropped.

### Coverage mismatches are surfaced, not hidden

IR runs can have different query sets (e.g. a re-run after a golden-set edit). Rows present in
only one run are shown in a separate "only in Run A / only in Run B" section rather than
being excluded or defaulting to zero — a missing query is a different signal than a zero score.

### Delta convention

`delta = run_B_value - run_A_value` for every shared metric. Positive = improvement, negative =
regression, colored accordingly (green positive, red negative, grey ~0 or not comparable).
Run A / Run B order is whatever the user picks in the two dropdowns — no forced chronological
ordering — since "which one is the baseline" is a user call, not something the tool infers.

### Default sort: biggest regression first

Default sort is by delta on the run type's primary metric, ascending (most negative /
worst regression first): `ndcg_cut_10` for IR, `faithfulness` for RAG. A column-header sort
control lets the user re-sort by any metric or delta, matching the existing Metrics tab's
sortable-table pattern.

### New UI surface: dedicated Compare tab

Added as a new tab in the existing tab shell (`RAG | Query | Ingest | Eval | Metrics | Compare`)
rather than folding into Metrics, since the layout (two run pickers, delta columns, expandable
content rows) is different enough from the single-run Metrics view to warrant its own space.
The existing Metrics tab is unchanged.

### Expandable content rows, not a permanent wide table

Metric + delta columns are always visible. Underlying content (question/answer/contexts or
retrieved sources) is shown when a row is expanded (click to toggle), keeping the default table
scannable while still making regressions explainable on demand.

---

## Functional Requirements

| # | Requirement |
|---|-------------|
| F1 | New endpoint `GET /api/eval/compare?type=ir\|rag&runA=<id>&runB=<id>` returns merged per-query rows with metrics for both runs, deltas, and content, or a structured error. |
| F2 | Request is rejected with a clear error if `runA`/`runB` don't share the same dataset, or don't both have the requested `type`'s result file. |
| F3 | IR comparison rows are keyed by `query_id`; rows present in only one run appear in an `only_in_a` / `only_in_b` list, not merged into the main table. |
| F4 | RAG comparison rows are keyed by list position; content (`question`, `answer`, `contexts`, `ground_truth`) for each side comes from that run's own `rag_results.json` at that position. |
| F5 | Every shared metric gets a `delta = b - a` value in the response; the response also states which measures are common to both runs (in case `measures` lists differ). |
| F6 | Compare tab lets the user pick a dataset, then Run A and Run B from that dataset's runs of one type (radio/toggle for IR vs RAG, filtering the run dropdowns). |
| F7 | Comparison table is sortable by any metric or delta column; default sort is worst-regression-first on the type's primary metric. |
| F8 | Each row can be expanded to show the underlying content (question/answer/contexts for RAG, retrieved source list for IR) for Run A and Run B side by side. |
| F9 | Coverage mismatch section (only-in-A / only-in-B) is visibly separated from the main comparison table, not interleaved. |
| F10 | All error states (missing run, mismatched dataset/type, malformed JSON) surface a human-readable message in the UI — no raw stack traces, no silent empty table. |
| F11 | A metric dropdown lets the user narrow the comparison table to a single measure's A/B/Δ columns, instead of showing every shared measure at once. |
| F12 | Every row (IR and RAG) displays the actual query text, not just an id — IR rows look it up from the dataset's `queries.jsonl`; RAG rows surface the `question` already present in `rag_results.json` directly in the main table row. |
| F13 | Clicking a `doc_id` inside an expanded IR row's source list fetches that document's title/text from the dataset's `corpus.jsonl` and displays it inline under the clicked entry. |
| F14 | Every row (IR and RAG) shows a "Judgement" link next to the query text in the main table row; clicking it toggles an inline panel with the gold judgement for that query, independent of the row's content-expansion accordion (Group 5). |
| F15 | For IR, the Judgement panel fetches relevance judgments (qrels) via `GET /api/eval/judgement?dataset=&queryId=`, showing `doc_id`/`score` pairs. For RAG, the panel shows the shared `ground_truth` text already present in the compare response (no fetch); flagged if Run A's and Run B's `ground_truth` differ at that position. RAG's per-run expanded content (Group 5.1) no longer duplicates `ground_truth`. |
| F16 | For IR, each `doc_id` inside the Judgement panel's qrels list is clickable: it fetches and inlines that document's title/text via the same `GET /api/eval/document` endpoint and client-side cache used by the source-list doc_id click (F13), so a document is fetched at most once per session regardless of which UI location triggered it. |

---

## Amendment (2026-07-11): Metric filter, query text display, document fetch-on-click

Three refinements requested after the initial spec, extending Group 4 (table columns) and
Group 5 (row expansion) below rather than changing the endpoint contract in F1–F10.

### Metric filter dropdown

The comparison table (Group 4) shows every shared measure as A/B/Δ columns. With four IR
measures or four RAG measures this is already wide; the dropdown gives the user a way to focus
on one measure at a time.

- Options: "All metrics" (default) plus one entry per value in the response's `measures` list.
- Selecting a metric narrows the table to `Query | <metric> A | <metric> B | <metric> Δ` —
  same rows, same sort order, fewer columns. It does **not** change which column drives sorting;
  the existing worst-regression-first default (per the type's primary metric) and any
  column-header sort the user has already applied both keep their current sort key. If that
  key's column happens to be hidden by the filter, the table stays sorted by it, just without a
  visible header to click — the user can still re-show it via "All metrics" or by picking that
  metric in the dropdown.
- This is purely a display filter; it changes nothing about the `/api/eval/compare` response or
  the only-in-A/only-in-B sections (which apply the same column filter).

### Query text display

Today IR rows show only `query_id` (e.g. `PLAIN-2`); RAG rows carry the real question text
(`question`) but only inside the expanded content, not in the main table row. Both are amended
so the actual query string is visible without expanding a row:

- **IR:** the backend loads `searchlab-eval/data/<dataset>/queries.jsonl` (BEIR format,
  `{"_id": ..., "text": ...}` per line) once per comparison request, builds a `query_id → text`
  map, and attaches `query_text` to every row, `only_in_a` entry, and `only_in_b` entry. If the
  dataset's `queries.jsonl` is missing, `query_text` is `null` and the UI falls back to showing
  just the `query_id` — this must not fail the whole comparison.
- **RAG:** `content_a["question"]` / `content_b["question"]` already exist at the same
  position; the row gets a top-level `query_text` field (sourced from `content_a`'s question)
  displayed in the main table's Query column. If `content_a["question"] != content_b["question"]`
  at the same index — a sign the two runs weren't sliced in the same order, undermining the
  positional-join assumption in "Row key differs by run type" above — the UI shows both,
  flagged, instead of silently picking one.

### Document fetch on doc_id click

IR row expansion (Group 5.1) shows ranked source lists (`doc_id`, `score`, `rank`) but not what
the document actually contains. Clicking a `doc_id` entry fetches and inlines that document's
content:

- New endpoint `GET /api/eval/document?dataset=<dataset>&docId=<doc_id>` reads
  `searchlab-eval/data/<dataset>/corpus.jsonl` (BEIR format, `{"_id", "title", "text"}` per
  line), finds the matching `_id`, and returns `{doc_id, title, text}`. This is a read from the
  static eval corpus, not the live OpenSearch index — it reflects what the dataset shipped with,
  not what's currently indexed (those can diverge after re-ingest; see caveat below).
- 404 if the dataset directory or `corpus.jsonl` is missing, or if `doc_id` isn't found in it —
  same human-readable-error convention as F10, not a stack trace.
- Clicking a `doc_id` row toggles an inline expansion directly under that entry showing
  `title` + `text`; clicking again collapses it. Fetched documents are cached client-side per
  `(dataset, doc_id)` for the session so re-clicking the same doc_id doesn't re-fetch.
- This adds one new read-only endpoint; it does not change `/api/eval/compare`'s response shape
  or write anything to disk, consistent with the rest of this feature being read-only.

---

## Amendment 2 (2026-07-11): Judgement panel (qrels for IR, ground_truth for RAG)

A fourth refinement, requested after the metric-filter/query-text/doc-fetch amendment above.
Both IR and RAG runs are scored against some form of gold judgement — qrels (relevance labels)
for IR, `ground_truth` for RAG — but neither was surfaced in the comparison view itself (qrels
weren't surfaced at all; `ground_truth` was only visible duplicated inside each run's expanded
content, per Group 5.1). This amendment adds a per-query "Judgement" link, next to the query
text in the main table row, that reveals the gold judgement on click — consistent with the
doc_id fetch-on-click pattern (Amendment 1) rather than an always-on column, since judgement
content is query-level (shared by both runs), not something that needs to compete for space
with the always-visible metric columns.

### Judgement link placement

- Added to the main table row's Query column (both IR and RAG), next to `query_text` —
  always visible, independent of whether the row's content-expansion accordion (Group 5) is
  open. Clicking toggles an inline panel directly under that row.
- Independent of the "only one row expanded at a time" accordion rule (Group 5.2): the
  judgement panel is a separate toggle and multiple rows' judgement panels may be open at once,
  same as doc_id inline expansions are independent of each other.

### IR: judgement = qrels

- New endpoint `GET /api/eval/judgement?dataset=<dataset>&queryId=<query_id>` reads
  `searchlab-eval/data/<dataset>/qrels/test.tsv` (BEIR TSV: `query-id`, `corpus-id`, `score`),
  filters to the requested `query_id`, and returns `{query_id, judgements: [{doc_id, score},
  ...]}`.
- 404 if the dataset directory or `qrels/test.tsv` is missing (structural absence). A `query_id`
  with zero matching rows is a normal data state, not an error: returns `200` with an empty
  `judgements` list, and the UI shows "No judgements recorded for this query" rather than
  treating it as a failure.
- The panel shows `doc_id | score` pairs so a user can cross-reference against the expanded
  source list's ranked `doc_id`s (if that row is also expanded) to see exactly which retrieved
  documents were and weren't gold-relevant.
- Cached client-side per `(dataset, query_id)` for the session, same convention as the doc_id
  fetch cache from Amendment 1.

### RAG: judgement = ground_truth (deduplicated, not re-fetched)

- `ground_truth` already arrives in `compare_rag`'s `content_a`/`content_b` (from
  `rag_results.json`); no new endpoint is needed. `compare_rag` adds a top-level `ground_truth`
  field per row (sourced from `content_a["ground_truth"]`), plus `ground_truth_mismatch: True`
  if `content_a["ground_truth"] != content_b["ground_truth"]` at that position — same pattern as
  the `query_text_mismatch` check in Amendment 1, since a mismatch here means the two runs
  weren't sliced identically.
- **This changes Group 5.1's existing RAG row-expansion content:** `ground_truth` is removed
  from the per-run Run A / Run B columns (previously duplicated — same text shown twice) and
  shown once, in the Judgement panel, since it is query-level truth rather than a run-level
  output like `answer`/`contexts`. Run A/B columns in the expanded content now show `answer` /
  `contexts` only.
- Clicking the Judgement link toggles the panel using data already present in the compare
  response (no fetch, no loading state) — unlike the IR case, which requires
  `GET /api/eval/judgement`.

### Non-goals for this amendment

- No new "judged relevance" derived metric (e.g. judged-precision@10) is added to the metric
  columns — this amendment surfaces the existing gold labels for inspection, it does not compute
  a new comparable number from them. That was considered (see prior brainstorm) and deferred as
  a heavier follow-up if the plain qrels/ground_truth view proves insufficient.
- No change to `/api/eval/compare`'s existing fields other than the additive `ground_truth` /
  `ground_truth_mismatch` on RAG rows described above.

---

## Amendment 3 (2026-07-11): Clickable `doc_id` inside the IR Judgement panel

A follow-up to Amendment 2's Judgement panel (F15). The IR Judgement panel shows `doc_id`/`score`
pairs from qrels, but those `doc_id`s were plain text — a user wanting to see what a judged
document actually contains had to separately expand the row's source list and hope the same
`doc_id` appeared there. This amendment makes qrels `doc_id`s clickable, directly reusing the
document fetch-on-click behavior already built for the source list (Amendment 1 / F13), rather
than inventing a second way to view a document.

This applies to **IR only** — the RAG Judgement panel shows `ground_truth` text and has no
`doc_id`s, so there is nothing to make clickable there.

- Clicking a `doc_id` inside the IR Judgement panel's qrels list behaves identically to clicking
  a `doc_id` in the row's expanded source list: it fetches `GET /api/eval/document?dataset=&docId=`
  and toggles an inline block showing `title` + `text` directly under the clicked judgement entry;
  clicking again collapses it.
- The client-side document cache is **shared** with the source-list `doc_id` cache from Amendment
  1 — keyed by `(dataset, doc_id)` regardless of which UI location (Judgement panel or source
  list) triggered the fetch, so a document already fetched via one path is not re-fetched via the
  other.
- Multiple judgement `doc_id` entries may be expanded at once within a single open Judgement
  panel — consistent with the existing rule that `doc_id` inline expansions are independent of
  each other (Amendment 1).
- Same error handling as Amendment 1: a lightweight inline "loading…" state, and on 404 an inline
  "Document not found" message rather than blocking the whole panel.
- No change to `/api/eval/judgement`'s response shape or `/api/eval/document`'s behavior — this
  is purely a UI wiring change reusing both existing endpoints and the existing cache.

---

## Amendment 4 (2026-07-14): Real OpenSearch match highlighting for IR documents

A fourth refinement. Amendments 1–3 let a user open a document's plain `title`/`text` (from the
static `corpus.jsonl`) by clicking a `doc_id` in either the source list or the IR Judgement
panel, but that view never explains *why* the document matched the query — no indication of
which terms overlapped. `raw_results.json` never stored highlight fragments (it only has
`doc_id`/`score`/`rank`), and the eval harness never talks to OpenSearch directly (`searchlab-eval`
calls the service's own `/api/query` HTTP endpoint, which itself issues a plain `match` query
with no `highlight` clause). So there is no highlight data sitting on disk to surface — getting a
"real" highlight (OpenSearch's own highlighter, not a naive frontend keyword-bold) requires
issuing a live OpenSearch query for that specific `doc_id` + query text at click time.

This is **IR only**. RAG rows have no per-document search step to attach a highlight clause to —
`question`/`answer`/`contexts` are already fully-formed inline text from `rag_results.json`, not
the result of a live per-document OpenSearch query. No RAG changes in this amendment.

### Live-index caveat

Same caveat class as the existing document-fetch feature (see Out of Scope, "Document fetch
reflecting the live OpenSearch index"): the highlight is computed against whatever is in the live
index *now*, which can differ from the static corpus the run was originally scored against if the
index was re-ingested since. This is a preview of matching, not a re-verification of the score —
acceptable for the same reason the plain document-fetch view already accepts it.

### On-demand, not precomputed

Highlighting is fetched together with the existing on-demand document fetch (Amendment 1 / F13)
when a `doc_id` row is expanded — not a separate user action, and not precomputed for every row
up front (which would mean one live OpenSearch query per row on every comparison load). Because
both the source-list `doc_id` click and the IR Judgement panel's `doc_id` click already funnel
through the same expansion handler (unified in Amendment 3), this highlighting is available from
both locations without separate wiring.

| # | Requirement |
|---|-------------|
| F17 | New endpoint `GET /api/eval/highlight?dataset=<dataset>&docId=<doc_id>&query=<text>` issues a live OpenSearch query scoped to that one `doc_id`, with a `highlight` clause on the same field (`chunk_text`) the live Query tab searches, and returns matched fragments. IR only; fetched automatically alongside the existing document fetch when a row's `doc_id` entry is expanded (source list or Judgement panel), not a separate click. |
| F18 | Highlight fetch failures degrade gracefully, never blocking the plain document text already shown: 404 if the `doc_id` no longer exists in the live index at all; a `200` with an empty fragment list if the document exists but its live content doesn't match the query text (a valid outcome, not an error) — rendered as "No live-index match for this query" rather than a blank section. |

---

## Amendment 5 (2026-07-14): Cross-reference highlighting between Judgement and retrieved results

A fifth refinement. Amendment 2 (F15) noted that the Judgement panel's qrels list lets "a user
cross-reference against the expanded source list's ranked `doc_id`s ... to see exactly which
retrieved documents were and weren't gold-relevant" — but that cross-referencing was left as a
manual, eyeball-both-lists exercise. This amendment automates it: `doc_id`s that appear in both
the row's Judgement (qrels) data and its retrieved source list are visually highlighted in each
list, so the overlap is visible at a glance instead of requiring the user to hold two `doc_id`
lists in their head simultaneously.

This is **IR only** — RAG rows have no qrels/source-list concept (RAG's "judgement" is the
`ground_truth` text, and there is no per-document retrieved list to cross-reference it against).

### Two directions of highlighting

- **In the row's expanded source list** (Group 5.1 / `renderSourceList`): each `doc_id` that also
  appears in that query's qrels is marked as judged — distinguishing a qrels score `> 0`
  ("judged relevant") from a qrels score of exactly `0` ("explicitly judged non-relevant"), since
  BEIR qrels files can list explicit zero-relevance judgements and collapsing that into one
  generic "judged" badge would hide the distinction that matters most (a highly-ranked retrieved
  doc that was explicitly judged non-relevant is a different signal than one nobody judged at
  all). This applies independently to Run A's and Run B's source list, since `sources_a` /
  `sources_b` are per-run.
- **In the Judgement panel's qrels list** (`renderJudgementPanel`): each `doc_id` that also
  appears in the row's `sources_a` and/or `sources_b` is marked as retrieved, showing which run(s)
  retrieved it and at what rank (e.g. "Retrieved: Run A rank 3, Run B rank 7" or just one side if
  only one run retrieved it).

### No backend or endpoint changes

Both data sources this cross-reference needs already exist client-side once fetched — `sources_a`
/ `sources_b` arrive in the initial `/api/eval/compare` response (no fetch needed), and qrels are
already fetched via the existing `GET /api/eval/judgement` endpoint (Amendment 2 / F15) and cached
client-side. This amendment adds no new endpoint, and no new field to `/api/eval/compare`'s or
`/api/eval/judgement`'s response shape — it is purely a client-side rendering change that
cross-references data already present in two existing caches.

### Judgement data must be available before the source list can mark it

Because qrels are only fetched when the Judgement panel is opened (Amendment 2), a user who
expands a row's source list *without* ever opening its Judgement panel would see no judged-status
marks — the qrels simply haven't been fetched yet. To avoid that dead end, expanding a row's
content (Group 5.2, `toggleCompareRow`) for an IR row also triggers a background qrels fetch for
that row's `query_id` (if not already cached), the same way expanding a `doc_id` already triggers
a concurrent highlight fetch alongside the document fetch (Amendment 4 / `toggleCompareDoc`). The
source list itself renders without judged-status marks while that fetch is in flight (same
"degrade gracefully, don't block" convention as every other on-demand fetch in this feature) and
re-renders with marks once it resolves. Opening the Judgement panel needs no equivalent
trigger in the other direction, since `sources_a`/`sources_b` are already available with no fetch.

| # | Requirement |
|---|-------------|
| F19 | In an IR row's expanded source list, each `doc_id` also present in that query's qrels is visually marked as judged, distinguishing score `> 0` ("judged relevant") from score `== 0` ("judged non-relevant") — per run (`sources_a` and `sources_b` marked independently). Expanding a row's content triggers a background qrels fetch (if not already cached) so this marking doesn't depend on the user having separately opened the Judgement panel first. |
| F20 | In an IR row's Judgement panel, each qrels `doc_id` also present in `sources_a` and/or `sources_b` is visually marked as retrieved, showing which run(s) retrieved it and at what rank. Uses data already present in the compare response and the existing qrels cache — no new fetch. |

---

## Amendment 6 (2026-07-16): Aggregate metrics comparison and improved/regressed filter

A sixth refinement. Amendments 1–5 all operate at the per-query row level; there was still no
way to see the two runs' overall (aggregate) numbers side by side without leaving the Compare
tab and opening each run's Metrics tab separately, and no way to narrow the per-query table to
just the queries that got better or worse in Run B without eyeballing every Δ cell. Both
`ir_scores.json` and `rag_scores.json` already carry a top-level `aggregate` dict (the same
numbers the Metrics tab's single-run view renders) alongside `per_query` — this amendment
surfaces that existing data rather than computing anything new.

### Aggregate metrics comparison

- `/api/eval/compare` gains three additive top-level fields — `aggregate_a`, `aggregate_b`,
  `aggregate_delta` — one entry per shared measure (the same `measures` intersection already
  used for per-query rows), sourced directly from each run's own `aggregate` dict in
  `ir_scores.json` / `rag_scores.json`. `aggregate_delta` uses the same `delta = b - a`
  convention as every other delta in this feature.
- The Compare tab renders these as a summary block above the per-query table: measure name,
  Run A value, Run B value, Δ (colored with the same red/green/grey convention as the per-query
  Δ columns). It is always visible once a comparison has been run, and shows **all** shared
  measures regardless of the per-query metric-column filter (existing Amendment 1 / F11
  dropdown) — that filter exists to keep a 50+ row table scannable; the aggregate block is a
  single compact row, so there is no width problem for it to solve.
- No new endpoint. No change to `ir_scores.json` / `rag_scores.json` — `aggregate` already
  exists in both; this only exposes it through the comparison response.

### Improved-in-B / regressed-in-B filter

- A three-way toggle — **All / Improved in B / Regressed in B** — sits next to the existing
  metric-column dropdown (F11). Default is **All** (identical to today's behavior).
- The filter judges each row by whichever metric currently drives the metric-column dropdown: if
  a specific measure is selected there, the filter uses that measure's delta; if the dropdown is
  on "All metrics", the filter falls back to the run type's primary measure (`ndcg_cut_10` for
  IR, `faithfulness` for RAG) — the same measure that already drives the default sort (see
  "Default sort: biggest regression first" above). Changing the metric dropdown while a non-All
  filter is active re-evaluates the filter against the newly selected metric.
- Threshold: reuses the existing "grey / not comparable" band already used for Δ cell coloring
  (`|delta| < 0.01`, Plan 4.2) rather than introducing a second threshold constant. A row is
  "Improved in B" if the active metric's delta is `> 0.01`, "Regressed in B" if `< -0.01`. Rows
  inside the grey band, or where the active metric isn't comparable for that row (missing on one
  side, so no `delta` entry exists), are excluded from both filtered views — they remain visible
  only under "All", matching the existing grey/non-comparable visual treatment.
- This is a display-only filter, exactly like the metric-column filter: it changes which rows of
  the already-fetched main table render, not the `/api/eval/compare` response, sort order, or the
  only-in-A/only-in-B sections. Those sections have no Run B side to judge "improved" or
  "regressed" against, so the toggle has no effect on them — they remain fully visible in every
  filter state.

| # | Requirement |
|---|-------------|
| F21 | `/api/eval/compare` response includes `aggregate_a`, `aggregate_b`, `aggregate_delta` — one entry per shared measure, sourced from each run's own top-level `aggregate` dict (already present in `ir_scores.json`/`rag_scores.json`), with `aggregate_delta = b - a`. Applies to both IR and RAG. |
| F22 | The Compare tab shows an aggregate summary block (measure / A / B / Δ, same delta color convention as per-query columns) above the per-query table, always visible once a comparison has run, showing all shared measures regardless of the per-query metric-column filter's current selection. |
| F23 | A three-way "All / Improved in B / Regressed in B" toggle next to the metric-column dropdown filters the main table's rows by the delta of whichever metric currently drives that dropdown (falling back to the type's primary measure when the dropdown is on "All metrics"), using the existing `|delta| < 0.01` grey-zone threshold to decide improved vs. regressed vs. excluded. |
| F24 | The improved/regressed filter is display-only (no re-fetch, no change to sort order or to which measure the table is sorted by) and does not affect the only-in-A/only-in-B sections, which have no Run A/B delta to filter on and remain fully visible in every filter state. |

---

## Amendment 7 (2026-07-17): Zero-value metric counts

A seventh refinement. A query scoring exactly `0` on a measure (e.g. `ndcg_cut_10 == 0`, meaning
nothing relevant was retrieved at all) is a qualitatively different failure than a query that
merely regressed — it's a complete miss. The per-query table already lets a user find individual
zero-scoring rows by sorting or filtering, but there was no quick way to see *how many* zero
scores each run has for a given measure without counting rows by hand. Both `ir_scores.json` and
`rag_scores.json` already carry the full `per_query` dict this count is computed from — this
amendment adds a derived count, not new source data.

- `/api/eval/compare` gains two additive top-level fields — `zero_counts_a`, `zero_counts_b` —
  one entry per shared measure, counting how many entries in that run's own `per_query` dict have
  that measure present and equal to exactly `0`. A missing or `None` value for a measure is not
  counted (a query that wasn't scored is a different signal than a query that scored zero).
- This is a per-run count over that run's **entire** `per_query` dict, not just the rows shared
  with the other run — an only-in-A or only-in-B query still counts toward its own run's total,
  consistent with the count being a property of one run, not of the comparison join.
- The Compare tab's aggregate summary block (Amendment 6) gains two more columns, "Zero in A" /
  "Zero in B", shown as plain counts (no delta color coding — a count isn't a delta) next to the
  existing measure/A/B/Δ columns. Same visibility rule as the rest of that block: always shows all
  shared measures, unaffected by the per-query metric-column filter (F11) and the
  improved/regressed row filter (F23).
- No new endpoint. No change to `ir_scores.json` / `rag_scores.json`.

| # | Requirement |
|---|-------------|
| F25 | `/api/eval/compare` response includes `zero_counts_a`, `zero_counts_b` — one entry per shared measure, counting each run's own `per_query` entries where that measure is present and equal to exactly `0` (missing/`None` values excluded). Applies to both IR and RAG. The Compare tab's aggregate summary block shows these as "Zero in A"/"Zero in B" columns, unaffected by the metric-column filter or the improved/regressed row filter. |

---

## Out of Scope

| Item | Notes |
|------|-------|
| Comparing IR vs RAG runs | Different metric sets; not a meaningful comparison |
| Comparing runs across datasets | Query IDs/questions don't correspond across datasets |
| Comparing more than two runs at once | Two-way comparison only; N-way is a future extension if needed |
| Changes to how runs are generated | `searchlab-eval download/ingest/query/ragas` and their output schemas are unchanged |
| Persisting comparisons | Comparison is computed on demand from existing JSON files; nothing new is written to disk |
| Statistical significance testing on deltas | Raw delta display only; no confidence intervals or significance tests in this pass |
| Document fetch reflecting the live OpenSearch index | `GET /api/eval/document` reads the static `corpus.jsonl` the dataset shipped with, not the current index state; if a document was re-ingested/edited since, this can diverge — acceptable since the eval scores themselves were computed against that same static corpus |
| Match highlighting reflecting the score-time index state | `GET /api/eval/highlight` (Amendment 4) queries the live index at click time, same divergence risk as document fetch above — it explains current matching, not what was true when the run was scored |
| Match highlighting for RAG rows | RAG content (`question`/`answer`/`contexts`) is already fully-formed inline text, not the result of a per-document OpenSearch query — there is no query to attach a `highlight` clause to |
| Judgement/retrieved cross-reference highlighting for RAG rows | RAG has no qrels or per-document retrieved list — `ground_truth` is compared as text, not cross-referenced against a doc_id list |
