# Per-Query Run Comparison: Validation

> Per the Constitution (Section VII), a phase is not complete because the code works.
> Every criterion below must pass before this work is merged.

---

## Acceptance Criteria

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| AC1 | `GET /api/eval/compare?type=ir&runA=&runB=` returns merged per-query rows for two IR runs of the same dataset | 200 with `rows`, `only_in_a`, `only_in_b`, `measures` populated | Crash, wrong schema, or missing fields |
| AC2 | `GET /api/eval/compare?type=rag&runA=&runB=` returns merged per-query rows for two RAG runs of the same dataset | 200 with content (`question`/`answer`/`contexts`/`ground_truth`) attached per row | Missing content, wrong index alignment |
| AC3 | Comparing runs from different datasets is rejected | 400, message names both datasets | Silent mismatch or crash |
| AC4 | Comparing an IR run against a RAG run (wrong `type` for one run) is rejected | 400, clear message | Crash or nonsensical merged row |
| AC5 | Missing `runA` or `runB` produces a clear error | 404 naming the missing run | Crash or empty 200 |
| AC6 | IR rows are keyed by `query_id`; queries present in only one run appear in `only_in_a`/`only_in_b`, not merged | Verified against a pair of runs with known differing query sets | Missing row silently dropped or zero-filled |
| AC7 | RAG rows are keyed by position; runs with different `--slice` sizes compare only the overlapping prefix, extra rows appear in only_in_a/only_in_b | Verified with two RAG runs of different slice sizes | Index-out-of-range crash or silent truncation without surfacing extra rows |
| AC8 | Delta = B − A for every shared measure, correctly signed | Spot-check 3+ rows against source JSON by hand | Sign flipped or wrong measure matched |
| AC9 | Compare tab run dropdowns filter correctly by dataset + type | Only IR runs shown when IR selected, only matching dataset's runs shown | Wrong runs listed, or all runs listed regardless of filter |
| AC10 | Table default-sorts worst-regression-first on the type's primary metric | `ndcg_cut_10` ascending delta for IR, `faithfulness` ascending delta for RAG | Wrong default sort or unsorted |
| AC11 | Column headers re-sort the table | Clicking any metric/delta header re-sorts ascending/descending | Sort does nothing or sorts wrong column |
| AC12 | Row expansion shows correct side-by-side content | RAG: question/answer/contexts/ground_truth for A and B; IR: ranked source lists for A and B | Wrong run's content shown, or blank on expand |
| AC13 | Existing Metrics, Eval, RAG, Query, Ingest tabs unaffected | No visual or functional regression in other tabs | Any regression in unrelated tabs |
| AC14 | No new files written to disk by the comparison feature | `searchlab-eval/results/` unchanged after using Compare tab | Any new/modified file under `results/` |
| AC15 | Metric dropdown narrows the table to one measure's A/B/Δ columns | Selecting a metric hides all other measure columns; "All metrics" restores them; row order/sort unchanged | Wrong columns shown, rows re-sorted/re-fetched, or dropdown has no effect |
| AC16 | IR rows show the actual query text next to `query_id` | Text matches the corresponding `_id` entry in `searchlab-eval/data/<dataset>/queries.jsonl` | Wrong text, missing text without fallback, or crash when `queries.jsonl` absent |
| AC17 | RAG rows show `question` text in the main table row (not only on expand) | Text visible without expanding; a Run A/B question mismatch at the same index is visibly flagged | Text only visible on expand, or mismatch silently resolved to one side |
| AC18 | Clicking a `doc_id` in an expanded IR row fetches and displays that document | `GET /api/eval/document?dataset=&docId=` returns `{doc_id, title, text}` matching `corpus.jsonl`; UI shows it inline under the clicked entry; missing doc/dataset shows a clear inline error, not a crash | Wrong document, blank on click, or crash/stack trace on missing doc |
| AC19 | Clicking the Judgement link on an IR row fetches and displays qrels for that query | `GET /api/eval/judgement?dataset=&queryId=` returns `{query_id, judgements: [{doc_id, score}, ...]}` matching `qrels/test.tsv`; empty result shows "No judgements recorded"; missing qrels file shows a clear inline error, not a crash; panel toggle works independent of row-expansion accordion | Wrong/missing judgements, blank on click, crash on missing file, or panel tied to accordion state |
| AC20 | Clicking the Judgement link on a RAG row displays `ground_truth` without a network fetch | Text matches `rag_results.json`'s `ground_truth` at that position for both runs; a Run A/B mismatch is visibly flagged; `ground_truth` no longer appears duplicated inside the per-run expanded answer/contexts columns | Wrong/missing text, mismatch silently resolved to one side, extra network request made, or `ground_truth` still duplicated in expanded columns |
| AC21 | Clicking a `doc_id` inside the IR Judgement panel fetches and inlines that document's title/text | Behaves identically to the source-list `doc_id` click: `GET /api/eval/document` result shown inline under the clicked judgement entry; a doc already fetched via the source list is not re-fetched (shared cache); multiple judgement doc_id entries can be expanded at once; 404 shows a clear inline error | Blank on click, crash/stack trace, duplicate fetch of an already-cached doc, or only one judgement doc_id expandable at a time |
| AC22 | Expanding an IR `doc_id` (source list or Judgement panel) fetches and shows real OpenSearch match highlighting for that document + query | `GET /api/eval/highlight?dataset=&docId=&query=` returns `{doc_id, fragments}` with matched terms wrapped in `<em>`; UI renders fragments above the plain text, matched terms visually emphasized, all other content escaped (view source / inspect element shows no unescaped document text as live HTML); doc in live index but no term overlap → empty fragments rendered as "No live-index match for this query" (not blank, not an error); doc not in live index → clear inline 404 message; RAG rows show no highlight fetch at all (check DevTools Network tab) | Blank on click, raw unescaped HTML injected into the page, wrong document's fragments shown, crash/stack trace on missing doc, or a highlight request fired for a RAG row |
| AC23 | `doc_id`s common to an IR row's Judgement (qrels) data and its retrieved source list are visually marked in both places | Expanding a row's source list marks each `doc_id` also present in qrels, distinguishing score `>0` ("judged relevant") from score `==0` ("judged non-relevant"), independently for Run A and Run B; the Judgement panel marks each qrels `doc_id` also present in `sources_a`/`sources_b` with which run(s) retrieved it and at what rank; marking works regardless of which of the two (source list, Judgement panel) the user opens first, since expanding the source list triggers a background qrels fetch if not already cached; no new network endpoint is used (only the existing `/api/eval/judgement` fetch, now also triggered by row expansion); RAG rows show no such marking (no qrels/source-list concept) | No marks shown, marks wrong/inverted, marks require the Judgement panel to have been opened first (i.e. don't appear when only the source list was expanded), rank/run attribution wrong, or a new endpoint/request introduced |
| AC24 | `/api/eval/compare` includes `aggregate_a`/`aggregate_b`/`aggregate_delta` for both IR and RAG | Values match each run's own `aggregate` dict in `ir_scores.json`/`rag_scores.json` for every shared measure; `aggregate_delta[m] == aggregate_b[m] - aggregate_a[m]` | Missing fields, values not matching the source JSON, or wrong sign |
| AC25 | Compare tab renders an aggregate summary block above the per-query table | Shows measure / A / B / Δ for every shared measure, colored with the same convention as per-query Δ cells; stays showing all measures when the per-query metric-column filter (F11) is narrowed to one metric | Block missing, wrong values, or it gets narrowed by the per-query metric filter instead of staying independent |
| AC26 | "All / Improved in B / Regressed in B" toggle filters the main table correctly | Selecting "Improved in B" shows only rows where the active metric's delta is `> 0.01`; "Regressed in B" shows only rows with delta `< -0.01`; rows in the grey zone or without a comparable delta appear only under "All"; only-in-A/only-in-B sections stay fully visible in every filter state; switching the metric-column dropdown while a filter is active re-evaluates it against the new metric | Wrong rows included/excluded, threshold not matching the existing grey-zone constant, only-in-A/B sections affected by the toggle, or filter not re-evaluating on metric-dropdown change |

---

## Manual Verification

### 1. IR comparison — happy path

```bash
cd service
uv run searchlab serve
```

- Open the Compare tab, select **IR**, dataset `nfcorpus`.
- Pick two existing nfcorpus IR runs (e.g. `nfcorpus-20260619T200023Z` vs
  `nfcorpus-20260623T002234Z`) as Run A / Run B.
- Click Compare.

Check:
- Table renders with `Query | ndcg_cut_10 (A/B/Δ) | recall_10 (A/B/Δ) | ...` columns.
- Sorted worst-regression-first on `ndcg_cut_10` by default.
- Clicking a query row expands ranked source lists (`doc_id`, `score`, `rank`) for both runs.
- Clicking a column header re-sorts.

### 2. RAG comparison — happy path

- Select **RAG**, dataset `nfcorpus`, pick two `nfcorpus-ragas-*` runs.
- Click Compare.

Check:
- Table shows `faithfulness`/`answer_relevancy` (and `context_recall`/`context_precision` if
  present) with A/B/Δ columns.
- Expanding a row shows the shared `question`, then Run A's `answer`/`contexts`/`ground_truth`
  next to Run B's.
- If the two runs have different `--slice` sizes, confirm the extra rows from the longer run
  appear in the only-in-A/only-in-B section, not silently dropped.

### 3. Dataset mismatch rejected

- Attempt to compare an `nfcorpus` run against a `fiqa` run (edit the request or pick
  mismatched runs if the UI allows it).

Check: clear 400 error naming both datasets; no partial/garbage table rendered.

### 4. Type mismatch rejected

- Request `/api/eval/compare?type=ir&runA=<an nfcorpus IR run>&runB=<a RAG run>` directly.

Check: clear 400 error; UI's own dropdowns should make this hard to trigger by accident (dataset
+ type filtering), but the API must reject it regardless of what the frontend allows.

### 5. Missing run

- Request `/api/eval/compare?type=ir&runA=does-not-exist&runB=<a valid run>`.

Check: 404 naming the missing run id; no stack trace.

### 6. Coverage mismatch (IR)

- Pick two IR runs known to have different query sets (or temporarily edit a copy of one run's
  `ir_scores.json` to drop a query) and compare them.

Check: dropped/extra query appears in only-in-A/only-in-B section with its own metric values,
not merged into the main table and not silently absent from both.

### 7. No disk writes

```bash
find searchlab-eval/results -newer /tmp/marker  # touch /tmp/marker before step 1
```

Check: using the Compare tab for steps 1–6 above creates no new/modified files under
`searchlab-eval/results/`.

### 8. Regression check on existing tabs

- Click through RAG, Query, Ingest, Eval, Metrics tabs after this change.

Check: all behave exactly as before; no console errors; no layout shift from the new tab.

### 9. Metric filter, query text, document fetch (amendment, 2026-07-11)

- Run an IR comparison (as in step 1). Confirm each row shows the query's actual text (e.g.
  `PLAIN-2` — "Do Cholesterol Statin Drugs Cause Breast Cancer?"), matching
  `searchlab-eval/data/nfcorpus/queries.jsonl`.
- Use the metric dropdown to select a single measure (e.g. `ndcg_cut_10`). Confirm the table
  narrows to `Query | ndcg_cut_10 A | ndcg_cut_10 B | Δ` with the same rows in the same order;
  switch back to "All metrics" and confirm all measure columns return.
- Expand an IR row's source list and click a `doc_id` (e.g. `MED-14`). Confirm its title/text
  appears inline under that entry, matching the corresponding line in
  `searchlab-eval/data/nfcorpus/corpus.jsonl`. Click again to collapse. Click a second time to
  confirm it doesn't re-fetch (or re-fetches silently with identical content).
- Request `/api/eval/document?dataset=nfcorpus&docId=does-not-exist` directly — confirm a clear
  404, not a stack trace.
- Run a RAG comparison (as in step 2). Confirm the `question` text is visible in the main table
  row without expanding.

### 10. Judgement panel (amendment 2, 2026-07-11)

- Run an IR comparison (as in step 1). Click the "Judgement" link on a row with known qrels
  (e.g. `PLAIN-2`). Confirm the panel shows `doc_id`/`score` pairs matching
  `searchlab-eval/data/nfcorpus/qrels/test.tsv`. Confirm the panel opens/closes independent of
  the row's own content-expansion accordion (both can be open at once, or the Judgement panel
  alone).
- Click "Judgement" on a query with no qrels rows (if one exists in the dataset) — confirm "No
  judgements recorded for this query" instead of an empty-looking panel or error.
- Request `/api/eval/judgement?dataset=nfcorpus&queryId=does-not-exist` — confirm `200` with an
  empty `judgements` list (not a 404), since a valid query with no judged docs is not an error.
- Request `/api/eval/judgement?dataset=does-not-exist&queryId=PLAIN-2` — confirm a clear 404,
  not a stack trace.
- Run a RAG comparison (as in step 2). Click "Judgement" on a row — confirm `ground_truth` text
  appears with no network request (check DevTools Network tab). Expand that same row's content
  and confirm `answer`/`contexts` show per-run but `ground_truth` is no longer duplicated there.

### 11. Clickable doc_id inside the IR Judgement panel (amendment 3, 2026-07-11)

- Run an IR comparison (as in step 1). Open a row's Judgement panel and click a `doc_id` (e.g.
  `MED-14`). Confirm its title/text appears inline under that entry, matching
  `searchlab-eval/data/nfcorpus/corpus.jsonl`, identically to clicking the same `doc_id` in the
  row's expanded source list.
- Expand the row's source list first and click `MED-14` there (triggering a fetch), then open the
  Judgement panel and click `MED-14` again — confirm no second network request is made (check
  DevTools Network tab), since the cache is shared between the two UI locations.
- With the Judgement panel open, click two different `doc_id` entries — confirm both stay
  expanded at the same time (not an accordion).
- Click a `doc_id` in the Judgement panel that doesn't exist in `corpus.jsonl` (if reachable) —
  confirm a clear inline "Document not found" message, not a stack trace.

### 12. Real OpenSearch match highlighting (amendment 4, 2026-07-14)

- Run an IR comparison (as in step 1). Expand a row's source list and click a `doc_id` known to
  be relevant to that query (e.g. one of its judged qrels docs). Confirm highlighted match
  fragments (matched terms emphasized) appear above the plain title/text, and that they reflect
  the row's actual query text.
- Open DevTools → Elements and inspect the rendered fragment: confirm matched terms are inside
  real `<em>` tags but no other injected markup is present (i.e. the fragment isn't rendered via
  raw `innerHTML` of unescaped content).
- Click a `doc_id` whose content doesn't actually overlap with the query's terms (or temporarily
  test with an unrelated `doc_id`) — confirm "No live-index match for this query" instead of a
  blank section or error.
- Request `/api/eval/highlight?dataset=nfcorpus&docId=does-not-exist&query=test` directly —
  confirm a clear 404, not a stack trace.
- Open the IR Judgement panel (as in step 10) and click a `doc_id` there — confirm the same
  highlighting behavior as the source-list click (same endpoint, same escaping).
- Run a RAG comparison (as in step 2) and expand a row's content — confirm no
  `/api/eval/highlight` request is made (check DevTools Network tab); RAG has no doc_id click
  flow to trigger it from.

### 13. Judgement / retrieved cross-reference highlighting (amendment 5, 2026-07-14)

- Run an IR comparison (as in step 1). Pick a row whose query has qrels entries that also appear
  among its retrieved docs (e.g. a query where a judged-relevant doc was actually retrieved by
  Run A or Run B). Expand the row's source list **without** opening the Judgement panel first.
  Confirm a background `/api/eval/judgement` request fires (check DevTools Network tab) and, once
  it resolves, the overlapping `doc_id`(s) in the source list become visibly marked as judged
  (distinguish a score `>0` mark from a score `==0` mark if both are reachable in the dataset).
- Reload/reset state, then open the row's Judgement panel first (triggering the qrels fetch), then
  expand the source list. Confirm no duplicate `/api/eval/judgement` request fires (cache hit) and
  the source list is marked correctly immediately.
- With the Judgement panel open, confirm each qrels `doc_id` that's also in `sources_a` and/or
  `sources_b` shows which run(s) retrieved it and at what rank; a qrels `doc_id` not retrieved by
  either run shows no retrieved mark.
- Confirm the marking direction is per-run: a `doc_id` retrieved only by Run A shows a mark only
  on Run A's side of the source list (and in the Judgement panel, attributed to Run A only).
- Run a RAG comparison (as in step 2) and open a row's Judgement panel — confirm no cross-reference
  marking UI appears (no qrels/source-list concept for RAG).

### 14. Aggregate metrics comparison and improved/regressed filter (amendment 6, 2026-07-16)

- Run an IR comparison (as in step 1). Confirm a summary block above the per-query table shows
  each shared measure's aggregate A / B / Δ, matching the `aggregate` dict in each run's
  `ir_scores.json` by hand-check. Narrow the per-query metric-column dropdown to a single measure
  and confirm the aggregate block still shows all measures (unaffected by that filter).
- Use the "All / Improved in B / Regressed in B" toggle: select "Improved in B" and confirm only
  rows with the active metric's delta `> 0.01` are shown; select "Regressed in B" and confirm only
  rows with delta `< -0.01` are shown; confirm rows near zero delta (or missing a comparable
  value for that metric) appear only under "All". Confirm the only-in-A/only-in-B sections remain
  fully visible in all three filter states.
- With "Improved in B" active, switch the metric-column dropdown to a different measure and
  confirm the filtered row set updates to reflect the newly active metric's deltas (not the
  previous metric's).
- Run a RAG comparison (as in step 2) and repeat the aggregate-block and filter checks against
  `faithfulness`/`answer_relevancy` (and `context_recall`/`context_precision` if present).

---

## Merge Checklist

> A phase is done or it is in progress. There is no "almost done." — Constitution § X

- [ ] AC1–AC26 all pass.
- [ ] Manual verification steps 1–14 completed; pass/fail noted for each.
- [ ] `compare_ir` / `compare_rag` covered by unit tests: matched rows, only-in-A/B, dataset
      mismatch (`ValueError`), missing run (`FileNotFoundError`), `query_text` attachment,
      RAG question-mismatch flagging.
- [ ] `load_document` covered by unit tests: found, missing doc_id, missing dataset/corpus file.
- [ ] `load_qrels` covered by unit tests: found, query with zero judgements (empty list, not an
      error), missing dataset/qrels file (`FileNotFoundError`).
- [ ] `compare_rag` unit tests cover `ground_truth` attachment and `ground_truth_mismatch`
      flagging.
- [ ] `compare_ir` / `compare_rag` unit tests cover `aggregate_a`/`aggregate_b`/`aggregate_delta`
      computation against each run's own `aggregate` dict.
- [ ] `highlight_document` covered by unit tests: hit with highlighted terms, hit with no term
      overlap (empty fragments, not an error), doc not in index (`FileNotFoundError`).
- [ ] `GET /api/eval/highlight` covered: 200 with fragments, 200 with empty fragments, 404 on
      missing doc, invalid `dataset`/`docId` rejected the same way `/api/eval/document` is.
- [ ] Highlight fragment rendering is verified not to use raw `innerHTML` on unescaped document
      content (manual inspect-element check in step 12, or a frontend test if one exists).
- [ ] Judgement/retrieved cross-reference highlighting (Amendment 5) verified: source-list marks
      appear whether the Judgement panel was opened first or not (background fetch on row
      expansion, no duplicate fetch if already cached); Judgement panel marks show correct
      per-run retrieved status and rank; no marking or extra requests on RAG rows.
- [ ] No changes to `searchlab-eval` output schemas, `RagCommand`, or any existing eval command.
- [ ] No new files written to disk by the comparison feature.
- [ ] `docs/wiki.md` updated with the Compare tab's usage, the RAG positional-join caveat, the
      metric filter, query text display, doc_id fetch-on-click behavior, the Judgement panel
      (qrels for IR, ground_truth for RAG), real OpenSearch match highlighting (IR only, live
      index, on-demand), the Judgement/retrieved cross-reference highlighting (Amendment 5), and
      the aggregate metrics summary plus improved/regressed-in-B filter (Amendment 6).
- [ ] `prompts/history.md` updated with the prompt that initiated this session (Constitution
      § VII step 0).
