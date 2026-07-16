# Custom Run Name: Requirements

## Context

`searchlab-eval`'s `query` and `ragas` commands each auto-generate a `run_id` when one isn't
supplied — `{dataset}-{timestamp}` for `query` (`searchlab-eval/searchlab_eval/cli.py:124-125`) and
`{dataset}-ragas-{timestamp}` for `ragas` (`cli.py:212-213`) — and use it as the directory name
under `results/<run_id>/`. Both commands already accept a `--run-id` CLI flag to override this
(`cli.py:101`, `cli.py:203`), but nothing in the web UI or `POST`/stream routing wires that flag
through for these two operations.

The Eval tab (`service/searchlab/web/html.py:274-278`) has a single `Run ID (for Metrics)` text
input (`#eval-run-id`). Today it is read only when the `metrics` op runs
(`service/searchlab/web/routes.py:234-236`, `html.py:692`) — used to pick which *existing* run to
compute metrics for. It is not sent at all when starting `query` or `ragas`
(`html.py:678-693`), so every run started from the UI gets an opaque timestamp-based id, making it
hard to find a specific run later (e.g. to compare a BM25 shingles experiment against a baseline).

Guidance reference (per the prior Index Management spec's finding, still true — `specs/mission.md`
/ `specs/techstack.md` do not exist in this repo): `CONSTITUTION.md` (mission/principles) and
`README.md` (current Python/FastAPI/OpenSearch stack — supersedes `CONSTITUTION.md` §V's outdated
"Java 21 / Spring Boot" description).

---

## Objective

Let a user starting a `Query` or `RAG Eval` (ragas) run from the Eval tab give it a custom name,
so the run is easy to identify later in the Available Runs list, the Metrics tab, and Compare —
instead of only ever getting an opaque `<dataset>-<timestamp>` id.

---

## Scope Decisions

*(Each of the following was a direct question put to the user — see conversation.)*

### Branch: cut from `main`, not the in-progress BM25-Improvements branch

The session started on `2026-07-16-BM25-Improvements` with uncommitted work (a staged schema file
and a modified `index_registry.json`). That work is unrelated to this feature, so it was stashed
(`git stash` — "WIP on 2026-07-16-BM25-Improvements before branching custom-run-name off main") and
left untouched on its own branch. This feature's branch, `2026-07-16-custom-run-name`, was cut
directly from `main`.

### Feature is about eval run naming, not something else

Confirmed directly: "give custom run name" refers to the Eval tab's `Query` and `RAG Eval` (ragas)
operations and their `results/<run_id>/` directories — not index names (already covered by the
Index Management feature), dataset names, or anything else.

### The custom name *is* the `run_id` — not a separate label

No second "display label" concept is introduced. The text the user types becomes the literal
`results/<name>/` directory name, passed straight through as `--run-id <name>` to the existing CLI
flag. This keeps one identifier per run instead of two, and requires no new metadata file or schema
change — `run_id` is already the thing every other part of the system (Metrics, Compare, Available
Runs list) keys off.

### Applies to both `Query` and `RAG Eval` (ragas)

Both operations currently auto-generate their own independent `run_id` (`query`:
`{dataset}-{ts}`; `ragas`: `{dataset}-ragas-{ts}`) and both already have an unused `--run-id` CLI
flag. Both get custom naming in this pass — not just `Query`.

`Download`, `Ingest`, and `Metrics` are unaffected: `Download`/`Ingest` don't produce a
`results/<run_id>/` directory at all, and `Metrics` already consumes (rather than creates) a
`run_id` via the same `#eval-run-id` field.

### Blank name preserves today's behavior exactly

The name field is optional. Leaving it empty when starting `Query` or `RAG Eval` reproduces
current behavior byte-for-byte: the CLI auto-generates `{dataset}-{timestamp}` /
`{dataset}-ragas-{timestamp}`, exactly as it does today. No regression for anyone who ignores the
new capability.

### Collision is rejected, not silently overwritten

If the user supplies a name that collides with an existing `results/<name>/` directory, the run is
refused with a clear error — not silently reused or overwritten. This protects a previous run's
`raw_results.json` / `ir_scores.json` / `rag_scores.json` from being clobbered by a same-named
re-run. Collision is checked **before** any querying/generation work starts (not after), since
`query`/`ragas` can take a while and failing late would waste that work.

### Reuse the existing `#eval-run-id` field — no new UI control

The Eval tab already has exactly one run-id text input, currently labeled "Run ID (for Metrics)"
and used only by the `Metrics` op. This same field is reused for `Query`/`RAG Eval` as the optional
custom name, and relabeled to reflect the dual purpose (naming a new run, or pointing at an
existing one for Metrics). No second input is added — the existing placeholder
(`e.g. bm25_phase0`) already models a name, not a metrics-lookup id, so this is a small extension of
what the field already visually implies.

---

## Functional Requirements

| # | Requirement |
|---|-------------|
| F1 | The `query` CLI command, when passed a `--run-id` that already exists under `results/`, exits with a clear non-zero error and does **not** run any queries. |
| F2 | The `ragas` CLI command, when passed a `--run-id` that already exists under `results/`, exits with a clear non-zero error and does **not** generate/score any answers. |
| F3 | `service/searchlab/web/routes.py`'s `_build_eval_command` passes `--run-id <runId>` to the `query` subcommand when `runId` is non-empty; omits it (current behavior) when empty. |
| F4 | `_build_eval_command` passes `--run-id <runId>` to the `ragas` subcommand when `runId` is non-empty; omits it (current behavior) when empty. |
| F5 | The Eval tab's `#eval-run-id` field is sent as `runId` for the `query` and `ragas` ops (in addition to its existing use for `metrics`), read via `runEvalOp()` (`html.py:678-693`). |
| F6 | The `#eval-run-id` field's label is updated to reflect it now names a new run *or* selects an existing one for Metrics (e.g. "Run Name"), and its placeholder/help text makes clear it's optional for Query/RAG Eval. |
| F7 | A collision or invalid-name error from the CLI surfaces in the Eval tab's log box exactly as other CLI errors do today (SSE `event: error`, streamed stderr line) — no new error-handling path needed in the route layer. |
| F8 | Leaving `#eval-run-id` blank when running `Query` or `RAG Eval` produces the same `run_id` format as today (`{dataset}-{timestamp}` / `{dataset}-ragas-{timestamp}`) — verified byte-for-byte unchanged. |
| F9 | A successfully named run appears in the Available Runs list, Metrics tab's run dropdown, and Compare tab under the custom name, with no special-casing needed beyond what already reads `run_id` from `results/<run_id>/`. |

---

## Out of Scope

| Item | Notes |
|------|-------|
| Renaming an existing run after it's created | Not requested; would require moving/renaming the `results/<run_id>/` directory and updating any files that embed `run_id` internally |
| Custom naming for `Download` or `Ingest` | Neither produces a `results/<run_id>/` directory; no `run_id` concept applies to them |
| A separate display-label field distinct from `run_id` | Rejected in scope decisions above — the custom name *is* the `run_id` |
| Character-set validation beyond collision + path-safety | No enforced naming convention (e.g. lowercase-only) beyond rejecting path-traversal characters (`/`, `..`) and empty strings, mirroring the existing Compare feature's `run_id` validation (`routes.py:362-364`) |
| Auto-overwrite / "run again" semantics for a reused name | Explicitly rejected — collisions are hard errors, not silent overwrites |
