# Index Management: Validation

> Per the Constitution (Section VII), a phase is not complete because the code works.
> Every criterion below must pass before this work is merged.

---

## Acceptance Criteria

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| AC1 | `GET /api/indexes` returns every `searchlab-*` index with a live document count | 200 with `[{index, label, docCount, schemaSource, createdAt}, ...]`, counts match `_cat/indices` | Missing index, wrong count, crash |
| AC2 | Pre-existing indexes (created before this feature, no registry entry) still appear in the list | Shown with `schemaSource: "pre-existing"`, `label` = index name | Hidden from the list, or crash on missing registry metadata |
| AC3 | `POST /api/indexes` creates a new OpenSearch index from an uploaded raw schema JSON | Index exists in OpenSearch with the exact `settings`/`mappings` uploaded; response returns the full index name | Index not created, wrong mapping applied, crash |
| AC4 | Created index is recorded in the registry and immediately visible in `GET /api/indexes` and `GET /api/datasets` | Both endpoints reflect the new index without a server restart | Registry not written, or endpoints stale |
| AC5 | Invalid index name/key is rejected before any OpenSearch call | 400 with a specific message (empty, bad characters, reserved key) | Crash, or an OpenSearch index created with an invalid/unintended name |
| AC6 | Duplicate index name/key is rejected | 400 naming the conflict; no overwrite of the existing index | Silent overwrite, data loss, or crash |
| AC7 | Invalid JSON in the uploaded schema file is rejected with a specific error | 400, parser error message shown; no index created | Crash, generic "failed" message, or partial index left behind |
| AC8 | A schema JSON that's valid JSON but an invalid OpenSearch index body is rejected | 400, OpenSearch's own error message surfaced; no index created | Crash, generic message, or partial/broken index left behind |
| AC9 | `GET /api/datasets` returns built-in entries (`default`, `nfcorpus`, `fiqa`) plus every registry entry | All expected keys present with correct labels | Missing built-ins, missing custom entries, duplicate keys |
| AC10 | RAG, Query, and Ingest tabs' dataset dropdowns are populated dynamically and include newly created indexes | Dropdown options match `GET /api/datasets` after a create | Dropdowns stuck on old hardcoded list, or newly created index absent |
| AC11 | Selecting a custom index in the RAG tab and asking a question searches that index | `POST /rag`'s `index` field in the response matches the custom index's full name | Wrong index searched, or 500/crash |
| AC12 | Selecting a custom index in the Query tab searches that index | `POST /api/query`'s `index` field in the response matches the custom index's full name | Wrong index searched, or 500/crash |
| AC13 | Ingest tab's new dataset selector routes PDF ingest to the chosen index | Chunks appear in the selected custom index (verify via `GET /api/indexes` doc count increasing) | Chunks land in the wrong (default) index despite a different selection |
| AC14 | Ingest tab defaults to the same behavior as before this change when the selector is left untouched | PDF lands in `config.index_name()` (`searchlab-v0` / `$SEARCHLAB_INDEX`), same as pre-change behavior | Default target changed unintentionally |
| AC15 | Eval, Metrics, and Compare tabs' dataset dropdowns are unchanged | Still list only `nfcorpus`/`fiqa` (or "All"), no custom indexes appear there | Custom indexes leak into these dropdowns, implying a false promise of eval support |
| AC16 | `index_chunks` / `index_corpus_docs` are unmodified — same document shape regardless of target index's schema | Diff shows no change to `service/searchlab/ingest/indexer.py`'s field set | Fields added/changed, silently expanding scope beyond this spec |
| AC17 | OpenSearch unreachable produces a clear error on both `GET /api/indexes` and `POST /api/indexes` | 502/400 with a readable message, no stack trace in the response | Crash, stack trace leaked to the client |

---

## Manual Verification

### 1. View existing indexes — happy path

```bash
docker compose up -d
cd service && uv run searchlab serve
```

- Ensure at least `searchlab-v0` exists (ingest the sample PDF once if needed:
  `./searchlab ingest test-corpus/sample.pdf`).
- Open the **Indexes** tab.

Check:
- `searchlab-v0` appears with a document count matching what was just ingested.
- If `searchlab-nfcorpus` / `searchlab-fiqa` exist from prior eval runs, they appear too, each
  showing `schemaSource: pre-existing` (or equivalent UI label) and their own doc counts.

### 2. Create an index from a schema file — happy path

Prepare a schema file, e.g. `/tmp/test-schema.json`:
```json
{
  "settings": { "number_of_shards": 1 },
  "mappings": { "properties": { "chunk_text": { "type": "text" } } }
}
```

- In the Indexes tab, enter name `my-test-idx`, choose the file, submit.

Check:
- Success message; index list refreshes and shows `searchlab-my-test-idx` with 0 documents.
- `curl http://localhost:9200/searchlab-my-test-idx/_mapping` shows the uploaded mapping applied
  exactly.
- Switch to the RAG or Query tab — `my-test-idx` (or its label) is now a selectable dataset
  option without reloading the page.

### 3. Duplicate name rejected

- Repeat step 2 with the same name `my-test-idx`.

Check: clear inline error naming the conflict; `GET /api/indexes` still shows exactly one
`searchlab-my-test-idx` entry (no duplicate, no overwrite).

### 4. Invalid schema JSON rejected

- Upload a file containing `{not valid json`.

Check: clear inline error describing the JSON parse failure; no new index created
(`GET /api/indexes` unchanged).

### 5. OpenSearch-rejected mapping

- Upload a file with a structurally invalid mapping, e.g.
  `{"mappings": {"properties": {"bad": {"type": "not-a-real-type"}}}}`.

Check: clear inline error surfacing OpenSearch's own rejection reason; no new index created.

### 6. Invalid index name rejected

- Attempt to create an index named `My Index!` (spaces/uppercase/punctuation) or an empty name.

Check: clear inline error before any network call reaches OpenSearch (or a clean 400 if
client-side validation is bypassed); nothing created.

### 7. Ingest routes to the selected custom index

- In the Ingest tab, select `my-test-idx` from the new dataset dropdown, ingest
  `test-corpus/sample.pdf`.

Check:
- Success message reports the target index as `searchlab-my-test-idx`.
- Indexes tab (refresh) shows `searchlab-my-test-idx`'s doc count increased by the chunk count
  reported.
- `searchlab-v0`'s doc count is unchanged.

### 8. Ingest default behavior preserved

- In the Ingest tab, leave the dataset dropdown on its default ("Default index"), ingest the
  sample PDF again.

Check: chunks land in `searchlab-v0` (or `$SEARCHLAB_INDEX`), exactly as before this feature
existed.

### 9. RAG/Query against a custom index

- In the Query tab, select `my-test-idx`, search any term.
- In the RAG tab, select `my-test-idx`, ask a question (requires `OPENAI_API_KEY`).

Check: both requests target `searchlab-my-test-idx` (visible in the response's `index` field);
results reflect whatever was ingested into it in step 7.

### 10. Eval/Metrics/Compare tabs unaffected

- Open Eval, Metrics, and Compare tabs.

Check: their dataset dropdowns still show only `nfcorpus`/`fiqa`/"All" — no custom indexes
listed; no regression in existing behavior (cross-check against the Compare feature's own
Validation.md steps if in doubt).

### 11. OpenSearch unreachable

```bash
docker compose stop
```

- Open the Indexes tab / attempt to create an index.

Check: clear error banner/message, no stack trace, no frozen UI.

```bash
docker compose start
```

---

## Merge Checklist

> A phase is done or it is in progress. There is no "almost done." — Constitution § X

- [ ] AC1–AC17 all pass.
- [ ] Manual verification steps 1–11 completed; pass/fail noted for each.
- [ ] `index_admin.create_index` covered by unit tests: success, invalid key, duplicate key,
      duplicate OpenSearch index, OpenSearch rejection propagated.
- [ ] `index_admin.list_indexes` covered by unit tests: merges registry metadata correctly,
      handles an index with no registry entry.
- [ ] `index_registry` covered by unit tests: load with missing file (`[]`), save + reload
      round-trip, `find_by_key` / `find_by_index` / `key_exists`.
- [ ] `_resolve_index` covered by unit tests: hardcoded `DATASET_INDEX` still wins over registry,
      registry key resolves correctly, unknown dataset falls back to default index (unchanged
      behavior).
- [ ] No changes to `index_chunks` / `index_corpus_docs` in `service/searchlab/ingest/indexer.py`.
- [ ] No changes to `searchlab-eval`'s behavior, CLI, or output schemas.
- [ ] `service/searchlab/data/` added to `.gitignore`; registry file is not committed.
- [ ] `docs/wiki.md` updated with the Indexes tab's usage, the `searchlab-<name>` naming
      convention, and the fixed-document-shape caveat for ingest into custom-schema indexes.
- [ ] `prompts/history.md` updated with the prompt that initiated this session (Constitution
      § VII step 0).
