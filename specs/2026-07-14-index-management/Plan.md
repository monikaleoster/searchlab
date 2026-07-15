# Index Management: Implementation Plan

> **Architecture decision:** Index creation/listing logic lives in a new
> `service/searchlab/opensearch/index_admin.py` module (mirrors how `compare.py` holds all
> comparison logic behind the `/api/eval/compare` route). A new file-backed registry
> (`service/searchlab/data/index_registry.json`, git-ignored) records indexes created through
> this feature, mirroring how `searchlab-eval/results/` records eval runs. The frontend gets one
> new tab (`Indexes`) plus dataset-dropdown changes to three existing tabs (RAG, Query, Ingest).

---

## Group 1 — Registry Module

**Where:** `service/searchlab/opensearch/index_registry.py` (new file)

1.1 `_REGISTRY_PATH` = `service/searchlab/data/index_registry.json`, resolved the same
    file-relative way `_REPO_ROOT` is computed in `routes.py`.

1.2 `load_registry() -> list[dict]` — reads and parses the JSON file; returns `[]` if the file or
    its parent directory doesn't exist (no error — an empty registry is the normal first-run
    state, same convention `eval_runs()` uses for a missing `results/` directory).

1.3 `save_entry(entry: dict) -> None` — appends one entry (`{index, key, label, createdAt,
    schemaSource}`) to the registry and writes it back atomically (write to a temp file in the
    same directory, then `os.replace`, to avoid a torn/partial file if the process is killed
    mid-write). Creates the parent directory if missing.

1.4 `find_by_key(key: str) -> dict | None` / `find_by_index(index_name: str) -> dict | None` —
    lookups used by `_resolve_index` (Group 4) and the list endpoint (Group 2).

1.5 `key_exists(key: str) -> bool` — used by create-index validation (Group 2.3) to reject
    duplicate keys before touching OpenSearch.

---

## Group 2 — Index Admin Module

**Where:** `service/searchlab/opensearch/index_admin.py` (new file)

2.1 `_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")` — index-key validation: lowercase
    letters/digits/hyphens only, must start with a letter or digit, 1–63 chars (OpenSearch index
    names top out at 255 bytes; 63 is a comfortable, readable ceiling matching `searchlab-<name>`
    staying well under that).

2.2 `validate_key(key: str) -> None` — raises `ValueError` with a specific message if the key is
    empty, fails `_NAME_RE`, or collides with a reserved key (`"default"`, `"nfcorpus"`,
    `"fiqa"` — the built-in dataset keys from `DATASET_INDEX`/`"default"`, to avoid a custom index
    silently shadowing a built-in dataset in the merged dropdown from Group 5).

2.3 `create_index(client, key: str, schema_body: dict) -> str` (returns the full index name):
    - `validate_key(key)`.
    - `full_name = f"searchlab-{key}"`.
    - Raises `ValueError` if `client.indices.exists(index=full_name)` or
      `index_registry.key_exists(key)` — duplicate name/key rejected before any create call.
    - Calls `client.indices.create(index=full_name, body=schema_body)`. Lets OpenSearch's own
      exception (`RequestError` from `opensearchpy`) propagate — the route layer (Group 3.2)
      catches it and turns it into a readable 400, since OpenSearch's own error message already
      names what's wrong with the mapping/settings.
    - Returns `full_name`; does **not** write the registry entry itself — that's the route's job
      (Group 3.2), after `create_index` succeeds, so a registry write failure doesn't leave an
      OpenSearch index silently untracked without the caller knowing which step failed.

2.4 `list_indexes(client) -> list[dict]`:
    - Calls `client.cat.indices(index="searchlab-*", format="json", h="index,docs.count")` — one
      call for all matching indexes' live doc counts (cheaper than one `count` call per index).
    - For each returned `{index, docs.count}`, looks up `index_registry.find_by_index(index)`;
      merges in `key`, `label`, `createdAt`, `schemaSource` if found, else `label = index`,
      `schemaSource = "pre-existing"`, `createdAt = None`.
    - Returns entries sorted by `index` name.

---

## Group 3 — Routes

**Where:** `service/searchlab/web/routes.py`

3.1 `GET /api/indexes`:
    ```python
    @router.get("/api/indexes")
    async def api_list_indexes():
        try:
            client = create_client()
            return list_indexes(client)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=502)
    ```
    A live-cluster failure here is a connectivity/cluster problem, not a user input problem —
    502, matching the "backend dependency unreachable" convention (distinct from the 400s used
    for bad user input elsewhere in this file).

3.2 `POST /api/indexes` (multipart form — first multipart endpoint in this file; existing
    endpoints use `Form`/`Body`, so this needs `UploadFile`/`File` from FastAPI):
    ```python
    @router.post("/api/indexes")
    async def api_create_index(
        name: str = Form(""),
        schemaFile: UploadFile = File(...),
    ):
        key = name.strip()
        raw = await schemaFile.read()
        try:
            schema_body = json.loads(raw)
        except json.JSONDecodeError as e:
            return JSONResponse({"error": f"Invalid JSON in schema file: {e}"}, status_code=400)
        try:
            client = create_client()
            full_name = create_index(client, key, schema_body)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        except OpenSearchException as e:
            return JSONResponse({"error": f"OpenSearch rejected the schema: {e}"}, status_code=400)
        save_entry({
            "index": full_name, "key": key, "label": key,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "schemaSource": "uploaded",
        })
        return {"index": full_name, "key": key}
    ```
    - `OpenSearchException` is `opensearchpy.exceptions.OpenSearchException` (base class covering
      `RequestError` for bad mappings) — imported alongside the existing `opensearchpy` usage.
    - No partial state on failure: the registry entry is only written after `create_index`
      returns successfully (per 2.3's note).

3.3 `GET /api/datasets`:
    ```python
    @router.get("/api/datasets")
    async def api_datasets():
        builtin = [
            {"key": "default", "label": "Default index"},
            {"key": "nfcorpus", "label": "nfcorpus"},
            {"key": "fiqa", "label": "FiQA-2018"},
        ]
        custom = [
            {"key": e["key"], "label": e["label"]}
            for e in load_registry()
        ]
        return builtin + custom
    ```
    This becomes the single source of truth the frontend uses to populate the RAG/Query/Ingest
    dataset dropdowns (Group 5), replacing the hardcoded `<option>` lists — but Eval/Metrics/
    Compare dropdowns (Group 5 note) are intentionally left as-is and do **not** call this
    endpoint, since their "dataset" concept requires local BEIR files this endpoint knows nothing
    about.

3.4 Extend `_resolve_index`:
    ```python
    def _resolve_index(dataset: str, default_index: str | None = None) -> str:
        if dataset == "default":
            return default_index or config.index_name()
        if dataset in DATASET_INDEX:
            return DATASET_INDEX[dataset]
        entry = index_registry.find_by_key(dataset)
        if entry:
            return entry["index"]
        return default_index or config.index_name()
    ```
    Registry lookup happens after the hardcoded dict (so `DATASET_INDEX` still wins if a future
    edit ever collides) and before the default-index fallback (so an unrecognized `dataset` value
    still behaves exactly as it does today — falls back rather than erroring, matching existing
    behavior for unknown dataset strings).

3.5 `POST /api/ingest` gains a `dataset: str = Form("default")` parameter, resolved via
    `_resolve_index(dataset)` instead of the current hardcoded `config.index_name()` — this is
    what makes F9 (Ingest tab dataset selector) actually route PDF ingest to the chosen index.

---

## Group 4 — Indexes Tab UI Shell

**Where:** `service/searchlab/web/html.py`

4.1 Add `Indexes` to the tab bar (`RAG | Query | Ingest | Eval | Metrics | Compare | Indexes`),
    same `data-tab`/`switchTab` pattern as the other tabs (`html.py:139-146`).

4.2 New `<div id="tab-indexes" class="panel hidden">` section, added after the Compare tab's
    closing `</div>` (`html.py` around line 384+), containing:
    - A "Create Index" card: name `<input>`, `<input type="file" accept="application/json">` for
      the schema, submit button, inline status/error area (`id="idx-create-status"`).
    - An "Existing Indexes" card: refresh button + `<table>` with columns Index, Label, Docs,
      Schema Source, Created At (`id="idx-table"`), mirroring the Eval tab's "Available Runs"
      card layout (`html.py:270-276`).

---

## Group 5 — Indexes Tab JS

**Where:** `service/searchlab/web/html.py` (embedded `<script>`)

5.1 `async function loadIndexes()` — `fetch('/api/indexes')`, renders rows into `#idx-table`;
    called on tab switch (extend `switchTab`'s existing per-tab load dispatch, same pattern
    already used for `loadEvalRuns()` when switching to the Eval tab) and on manual refresh click.

5.2 `async function createIndex()` — reads the name input + selected `File` object, builds a
    `FormData` (`formData.append('name', ...); formData.append('schemaFile', fileInput.files[0])`),
    `fetch('/api/indexes', {method: 'POST', body: formData})` — **no** `Content-Type` header set
    manually (the browser sets the multipart boundary itself; setting it explicitly is a classic
    bug that breaks multipart uploads). On success: clear the form, show a success message, call
    `loadIndexes()` and `loadDatasets()` (5.3) to refresh both the table and every dataset
    dropdown. On error: show the returned `error` message inline, same visual pattern as
    `ingest-status` (`html.py:235`).

5.3 `async function loadDatasets()` — `fetch('/api/datasets')`, populates the RAG (`#rag-dataset`,
    `html.py:160-164`), Query (`#q-dataset`, `html.py:195-198`), and new Ingest (`#ingest-dataset`,
    Group 6) `<select>` elements by replacing their `<option>` children with the fetched list
    (`key` → `value`, `label` → text). Called once on page load (alongside the existing
    `refreshCompareDatasetDropdown()` call already run at startup) and again after a successful
    `createIndex()` (5.2).

5.4 Preserve each dropdown's current selection across a `loadDatasets()` refresh (read
    `select.value` before replacing options, restore it after if that value still exists in the
    new list) — otherwise a user with the RAG tab's dataset already set would silently lose that
    selection every time someone creates an index in another tab/session state refresh.

---

## Group 6 — Ingest Tab: Add Dataset Selector

**Where:** `service/searchlab/web/html.py`

6.1 Add a dataset `<select id="ingest-dataset">` to the Ingest tab's form row
    (`html.py:220-237`), same `field-sm` styling as the RAG/Query tabs' dataset selectors,
    defaulting to `"default"` (Default index) — preserves today's behavior for anyone who
    doesn't touch the new dropdown.

6.2 `runIngest()` (`html.py:575`) includes the selected `ingest-dataset` value in its POST body
    to `/api/ingest` as the new `dataset` form field (Group 3.5).

6.3 Update the Ingest tab's explanatory copy (`html.py:223-226`, currently "Indexes a PDF into
    the default OpenSearch index...") to reflect that the target is now whatever's selected in
    the dataset dropdown.

---

## Group 7 — Error States

**Where:** `service/searchlab/web/html.py`, `routes.py`

7.1 Duplicate index name/key (`ValueError` from `create_index`) surfaces as a red inline message
    under the create-index form — e.g. "Index 'searchlab-nfcorpus' already exists." — not a
    silent no-op or overwrite.

7.2 Invalid JSON file and OpenSearch-rejected schema both surface the specific error text
    returned by the backend (parser error location, or OpenSearch's own mapping-error message)
    rather than a generic "creation failed."

7.3 `GET /api/indexes` / `GET /api/datasets` failures (OpenSearch unreachable) show a red banner
    on the Indexes tab, matching the existing Eval tab's error-banner convention — no raw stack
    trace.

---

## Group 8 — Housekeeping

8.1 Add `service/searchlab/data/` to `.gitignore` (root `.gitignore`, alongside the existing
    `searchlab-eval/results` entry) — the registry file is runtime state, not source.

8.2 `docs/wiki.md`: document the Indexes tab (how to view indexes, how to create one from a
    schema file, the naming convention `searchlab-<name>`, and the explicit caveat that ingest
    still writes its fixed document shape regardless of the uploaded schema's field names).

---

## Definition of Done

- [ ] `GET /api/indexes` lists every `searchlab-*` index with a live document count, merging
      registry metadata for indexes created through this feature
- [ ] `POST /api/indexes` creates a new index from an uploaded raw OpenSearch schema JSON + name
      field; rejects invalid names, duplicate names, invalid JSON, and OpenSearch-rejected
      mappings with clear, distinct error messages
- [ ] A successfully created index is recorded in `service/searchlab/data/index_registry.json`
      and immediately appears in both `GET /api/indexes` and `GET /api/datasets`
- [ ] `GET /api/datasets` returns the built-in BEIR entries plus every registry entry
- [ ] RAG, Query, and Ingest tabs' dataset dropdowns are populated from `GET /api/datasets`
      instead of hardcoded options, and a newly created index is selectable there without a
      restart or code change
- [ ] Ingest tab has a dataset selector; PDF ingest targets the selected index; default behavior
      (no selection change) still targets the same default index as before this change
- [ ] Eval, Metrics, and Compare tabs' dataset dropdowns are unchanged
- [ ] Indexes tab renders the index table and create-index form; both wired to the new endpoints
- [ ] No changes to `index_chunks` / `index_corpus_docs`'s document shape
- [ ] No changes to `searchlab-eval`'s behavior or output schemas
- [ ] Existing tests still pass; new unit tests cover `index_admin.create_index` /
      `list_indexes` and `index_registry`'s load/save/find functions
