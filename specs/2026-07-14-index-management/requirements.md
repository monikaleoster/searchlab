# Index Management: Requirements

## Context

Today OpenSearch indexes exist implicitly. The default PDF index (`searchlab-v0` /
`$SEARCHLAB_INDEX`) is created lazily by `ensure_index_exists` on first PDF ingest
(`service/searchlab/opensearch/index_bootstrap.py`) with one fixed hardcoded mapping
(`INDEX_MAPPING`). Per-dataset eval indexes (`searchlab-nfcorpus`, `searchlab-fiqa`) are created
the same way by `/api/corpus-ingest`, driven by a hardcoded `DATASET_INDEX` dict in
`service/searchlab/web/routes.py`. There is no UI or endpoint to see what indexes exist, how many
documents are in them, or to create one with a custom mapping/settings — a new index only comes
into being as a side effect of ingesting into it.

Guidance reference (per prior spec decision, still true — `specs/mission.md` / `specs/techstack.md`
do not exist in this repo): `CONSTITUTION.md` (mission/principles; note its "Java 21 / Spring Boot"
tech description predates the Python migration and is superseded by `README.md`'s Python/FastAPI/
OpenSearch stack, which is what this spec follows) and `README.md` (current tech stack and project
layout).

---

## Objective

Add an **Indexes** tab that lets a user:

1. **View existing indexes** — every `searchlab-*` OpenSearch index, with its live document count.
2. **Create a new index** by uploading a JSON file containing a raw OpenSearch index-creation body
   (`settings` / `mappings`), with a separate name field, via the browser.

A newly created index is also usable as a target dataset in the existing **RAG**, **Query**, and
**Ingest** tabs (not Eval/Metrics/Compare — see "Eval tabs are out of reach" below).

---

## Scope Decisions

*(Each of the following was a direct question put to the user — see conversation — except
"Eval tabs are out of reach," which is a structural consequence of the codebase, documented here
for visibility rather than asked as a preference.)*

### Index listing: searchlab-created indexes only, live discovery + registry merge

The list shows only indexes matching the `searchlab-*` naming convention this app already uses
(not every index on the cluster — avoids surfacing OpenSearch system indices or unrelated
indexes). It is **not** limited to indexes created through this feature's own create-index flow:
pre-existing indexes (`searchlab-nfcorpus`, `searchlab-fiqa`, `searchlab-v0`) must also appear,
since hiding them would make the feature useless for its stated purpose ("view existing
indexes"). The list endpoint queries OpenSearch directly (`cat.indices` with `docs.count`) for
live discovery, then enriches each entry with registry metadata (label, schema source, created-at)
when that index was created through this feature. Indexes with no registry entry still show, just
without that extra metadata.

### Schema file: raw OpenSearch index-creation body, applied as-is

The uploaded JSON is a literal OpenSearch create-index payload — `{"settings": {...}, "mappings":
{...}}` — passed to `client.indices.create()` unmodified. No simplified/translated schema format.
This gives full power (custom analyzers, arbitrary field types) at the cost of requiring the user
to know OpenSearch mapping syntax; validation is limited to "is this valid JSON" and "does
OpenSearch accept it," not schema-correctness checking.

### Index name: separate form field, not embedded in the JSON

The user types a short name (e.g. `my-index`) in a text field alongside the file upload. The
uploaded JSON contains only `settings`/`mappings` — no name field inside it is read. The backend
applies the existing naming convention (`searchlab-<name>`), consistent with `searchlab-nfcorpus`
/ `searchlab-fiqa` / `searchlab-v0`.

### Ingest keeps writing its existing fixed document shape

`index_chunks` / `index_corpus_docs` (`service/searchlab/ingest/indexer.py`) are **not** changed
to support arbitrary user-defined fields. Ingesting a PDF or BEIR corpus into a custom-schema
index still writes the same fixed shape it always has: `chunk_text`, `chunk_id`,
`source_filename`, `page_number`, `chunk_position`, `ingested_at`. The uploaded schema's practical
effect on ingest is therefore limited to whatever the user's `mappings`/`settings` do to those
same field names (e.g. a custom analyzer on `chunk_text`) plus OpenSearch's own dynamic mapping
for any fields the schema didn't declare. This is a real limitation, not hidden: a user who
uploads a schema expecting entirely different field names to be populated will get an index whose
custom fields stay empty. Documented as a caveat, not solved in this pass (see Out of Scope).

### Upload mechanism: browser file upload (multipart), not a server path

Unlike the existing PDF ingest field (which takes a server-relative path string), the schema JSON
is uploaded as file content from the browser (`multipart/form-data`) to a new endpoint — the
schema file lives on the user's machine, not the server's filesystem, so a path-based flow
wouldn't work the same way PDF ingest's does.

### Dataset/index registry: new persisted file, dynamically merged with hardcoded BEIR entries

A new JSON registry file (`service/searchlab/data/index_registry.json`, git-ignored, created
lazily — same pattern as `searchlab-eval/results/`) records indexes created through this feature:
`{index, key, label, createdAt, schemaSource}`. A new `GET /api/datasets` endpoint merges this
registry with the existing hardcoded BEIR entries (`nfcorpus`, `fiqa`, `default`) into one list.
The **RAG**, **Query**, and **Ingest** tabs' dataset dropdowns are populated from this endpoint
instead of their current hardcoded `<option>` lists, so a newly created index appears there
without a code change. The `_resolve_index` helper in `routes.py` is extended to also check the
registry (by `key`) after the hardcoded `DATASET_INDEX` dict, before falling back to
`config.index_name()`.

### Eval tabs are out of reach for custom indexes (structural, not a preference)

The **Eval**, **Metrics**, and **Compare** tabs' notion of "dataset" is tied to
`searchlab-eval/data/<dataset>/` — local `queries.jsonl`, `corpus.jsonl`, `qrels/test.tsv` files
the BEIR download step produces. A custom index created through this feature has no such files;
it is purely an OpenSearch index with whatever a user ingests into it via PDF/corpus ingest. So
integrating custom indexes into those three tabs' dataset pickers is not just deferred — it isn't
meaningful without also building a way to supply queries/qrels for a custom index, which is well
beyond this feature's objective. Their dropdowns are unchanged.

### Delete is out of scope for this pass

View + create only. No delete/drop-index UI or endpoint in this pass.

### UI placement: new "Indexes" tab

Added to the existing tab bar (`RAG | Query | Ingest | Eval | Metrics | Compare | Indexes`),
following the same pattern the Compare tab established.

---

## Functional Requirements

| # | Requirement |
|---|-------------|
| F1 | New endpoint `GET /api/indexes` returns every `searchlab-*` OpenSearch index with its live document count, merged with registry metadata (label, schema source, created-at) where available. |
| F2 | New endpoint `POST /api/indexes` accepts a multipart form (`name`, `schemaFile`) and creates a new OpenSearch index named `searchlab-<name>` using the uploaded JSON as the literal `settings`/`mappings` body. |
| F3 | Index name is validated (non-empty, safe characters only — e.g. lowercase letters, digits, hyphens; reject anything that isn't a valid OpenSearch index-name segment) before any OpenSearch call. |
| F4 | Creating an index whose name already exists (in OpenSearch or the registry) is rejected with a clear error, not a silent overwrite. |
| F5 | An uploaded file that isn't valid JSON, or JSON that OpenSearch rejects as an invalid index body (bad mapping/settings), produces a clear inline error — no stack trace, no partially-created index left behind (if OpenSearch's `indices.create` call fails, nothing is registered). |
| F6 | On success, the new index is recorded in `service/searchlab/data/index_registry.json` (index name, user-given key, label, created-at, schema source) so it can be listed with metadata and appear in dataset pickers. |
| F7 | New endpoint `GET /api/datasets` returns the merged list of built-in BEIR dataset entries (`default`, `nfcorpus`, `fiqa`) and registry-derived custom index entries, each with a `key` and display `label`. |
| F8 | The RAG, Query, and Ingest tabs' dataset dropdowns are populated from `GET /api/datasets` at page load, instead of hardcoded `<option>` lists — a newly created index appears without a code change. |
| F9 | The Ingest tab gains a dataset/index selector (it currently has none — PDF ingest always targets `config.index_name()`); PDF ingest targets whichever dataset/index is selected, defaulting to "Default index" to preserve today's behavior. |
| F10 | `_resolve_index` in `routes.py` is extended to resolve a registry `key` to its full index name, after the existing hardcoded `DATASET_INDEX` lookup, before falling back to the default index. |
| F11 | The Indexes tab shows a table: index name, label, live document count, schema source (e.g. "Uploaded" vs. "Pre-existing"), created-at — with a manual refresh control. |
| F12 | The Indexes tab has a create-index form: name field + file picker for the schema JSON + submit; shows success/error inline, and refreshes the index list and dataset dropdowns (F8) on success. |
| F13 | Eval, Metrics, and Compare tabs' dataset dropdowns are unchanged — they continue to list only BEIR-downloaded datasets, since those tabs depend on local `queries.jsonl`/`corpus.jsonl`/`qrels` files a custom index doesn't have. |

---

## Out of Scope

| Item | Notes |
|------|-------|
| Deleting/dropping an index | View + create only in this pass |
| Simplified/translated schema format | Uploaded JSON is applied as a raw OpenSearch index body, no field-list DSL |
| Arbitrary-field ingest | `index_chunks`/`index_corpus_docs` keep writing their existing fixed document shape regardless of the uploaded schema's field names |
| Schema-correctness validation beyond "OpenSearch accepts it" | No linting of the uploaded mapping against ingest's fixed field shape or against best practices |
| Wiring custom indexes into Eval/Metrics/Compare | Those tabs need local BEIR files (queries/corpus/qrels) a custom index doesn't have; structurally out of reach, not just deferred |
| Editing an existing index's settings/mappings after creation | Create-only; OpenSearch itself restricts most mapping changes post-creation anyway |
| Renaming an index | Not supported by OpenSearch directly (would require reindex); not attempted here |
| Cluster-wide index listing (non-`searchlab-*` indexes) | Only the app's own naming convention is surfaced |
