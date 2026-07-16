# Custom Run Name: Implementation Plan

> **Architecture decision:** No new modules. `--run-id` already exists as a CLI flag on both
> `query` and `ragas` (`searchlab-eval/searchlab_eval/cli.py`); this feature adds a collision
> guard around it and wires the existing (currently Metrics-only) `#eval-run-id` UI field through
> to those two ops. Everything routes through the same `_build_eval_command` /
> `/api/eval/stream` SSE path the Index Management and Compare features already extended.

---

## Group 1 — CLI: Run-ID Collision Guard

**Where:** `searchlab-eval/searchlab_eval/cli.py`

1.1 Add a module-level helper, placed above the `download` command (near the other shared
    constants at `cli.py:9-27`):

    ```python
    def _reject_if_run_exists(run_id: str) -> None:
        if ".." in run_id or "/" in run_id or "\\" in run_id:
            click.echo(f"Error: invalid run id '{run_id}'", err=True)
            sys.exit(1)
        if (Path("results") / run_id).exists():
            click.echo(f"Error: run '{run_id}' already exists — choose a different name", err=True)
            sys.exit(1)
    ```
    Path-traversal characters are rejected the same way `service/searchlab/web/routes.py:362-364`
    already rejects them for the Compare feature's `run_id` inputs — this CLI command can be
    invoked directly (not just via the web route), so the same guard belongs here too.

1.2 `query` command (`cli.py:103-125`): call `_reject_if_run_exists(run_id)` immediately after the
    `if run_id is None: run_id = ...` block, but only when `run_id` was **explicitly supplied**
    (i.e. wrap the call in `if run_id is not None` computed before the auto-generate branch, or
    equivalently structure as:
    ```python
    user_supplied = run_id is not None
    if run_id is None:
        run_id = f"{dataset}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    elif user_supplied:
        _reject_if_run_exists(run_id)
    ```
    so auto-generated timestamp ids are never subject to the check — they're already
    collision-free in practice, and today's behavior (silent `mkdir(exist_ok=True)`) must not
    change for the omitted-flag path (F8).

1.3 `ragas_cmd` (`cli.py:205-216`): same pattern — call `_reject_if_run_exists(run_id)` right
    after resolving `run_id`, guarded to only fire when the user passed `--run-id` explicitly.

1.4 Both commands' collision/invalid-name errors go to stderr via `click.echo(..., err=True)` +
    `sys.exit(1)`, matching the existing "queries not found" error pattern
    (`cli.py:118-120`) — no new error-reporting mechanism.

---

## Group 2 — Route: Wire `--run-id` Through for `query` and `ragas`

**Where:** `service/searchlab/web/routes.py`

2.1 `_build_eval_command` (`routes.py:219-243`): in the `"query"` case, append
    `["--run-id", run_id]` when `run_id` is truthy, mirroring the existing `index` handling in the
    same branch:
    ```python
    case "query":
        cmd = ["uv", "run", "searchlab-eval", "query", "--dataset", dataset]
        if index:
            cmd += ["--index", index]
        if run_id:
            cmd += ["--run-id", run_id]
    ```

2.2 Same change in the `"ragas"` case:
    ```python
    case "ragas":
        cmd = ["uv", "run", "searchlab-eval", "ragas", "--dataset", dataset]
        if slice_val:
            cmd += ["--slice", slice_val]
        if run_id:
            cmd += ["--run-id", run_id]
    ```

2.3 No signature change to `_build_eval_command` or `/api/eval/stream` — both already accept
    `run_id` / `runId` (`routes.py:219`, `routes.py:251`); this group only changes which `match`
    branches consume it.

---

## Group 3 — Eval Tab UI

**Where:** `service/searchlab/web/html.py`

3.1 Relabel the existing field (`html.py:275-278`) from "Run ID (for Metrics)" to "Run Name",
    and adjust the placeholder to signal it's optional for Query/RAG Eval:
    ```html
    <div class="field" style="flex:0 0 210px">
      <label for="eval-run-id">Run Name</label>
      <input type="text" id="eval-run-id" placeholder="optional, e.g. bm25_shingles" title="Custom name for a new Query/RAG Eval run, or the run to target for Compute Metrics" />
    </div>
    ```
    No new input element — same field now serves both purposes (naming a new run; selecting an
    existing one for Metrics), per the reuse decision in `requirements.md`.

3.2 `runEvalOp()` (`html.py:678-693`): change line 692's condition so `runId` is sent for
    `metrics`, `query`, and `ragas` (not just `metrics`):
    ```javascript
    if (op === 'metrics' || op === 'query' || op === 'ragas') {
      if (runId) url += `&runId=${enc(runId)}`;
    }
    ```
    Note the behavior split: `metrics` still requires a non-empty value (unchanged — enforced
    server-side by `_build_eval_command`'s existing `ValueError` at `routes.py:234-235`); `query`
    and `ragas` only append the param when non-empty, otherwise the URL is built exactly as today
    (F8).

---

## Group 4 — Tests

**Where:** `searchlab-eval/tests/test_cli.py`, `service/tests/test_routes.py`

4.1 `test_cli.py` — `query` collision guard, using the existing `CliRunner` pattern
    (`test_cli.py:5,24-29`) with `runner.isolated_filesystem()` or a `tmp_path`-backed `cwd`:
    - Running `query --dataset nfcorpus --run-id run1` when `results/run1/` already exists (with
      a `queries.jsonl` fixture present so the command reaches the collision check) exits
      non-zero and prints an error naming `run1`; no queries are executed (mock
      `run_queries`/`run_query` and assert not called).
    - Running `query --dataset nfcorpus --run-id run1` when `results/run1/` does **not** exist
      succeeds and creates `results/run1/raw_results.json`.
    - Running `query --dataset nfcorpus` with no `--run-id` and a pre-existing arbitrary
      `results/<something>/` directory still succeeds (auto-generated path is never subject to
      the guard) — regression check for F8.

4.2 `test_cli.py` — same three cases mirrored for `ragas_cmd`, mocking `generate`/`score` (per
    the existing pattern for isolating ragas from a live service/judge model, following whatever
    mocking approach the current `ragas` tests in this file already use, if present — otherwise
    patch `searchlab_eval.rag_eval.generate` and `searchlab_eval.rag_eval.score`).

4.3 `test_routes.py` — extend the `_build_eval_command` test block (`test_routes.py:49-83`,
    alongside the existing index-override tests) with:
    - `test_build_eval_command_query_appends_run_id_when_given` — asserts `--run-id run1` present.
    - `test_build_eval_command_query_omits_run_id_when_blank` — asserts `--run-id` absent,
      command identical to today's.
    - `test_build_eval_command_ragas_appends_run_id_when_given` / `..._omits_run_id_when_blank`
      — same two cases for the `ragas` branch.
    - `test_build_eval_command_ingest_unaffected_by_run_id` / `..._download_unaffected_by_run_id`
      — confirms `run_id` has no effect on the two ops that don't produce a `results/` directory,
      matching the existing "unaffected by index" tests' style (`test_routes.py:69-76`).

---

## Group 5 — Housekeeping

5.1 `docs/wiki.md` (if it documents the Eval tab's controls): note that the Run Name field now
    optionally names a new Query/RAG Eval run, in addition to its existing role selecting a run
    for Compute Metrics, and that a duplicate name is rejected rather than overwritten.

5.2 `prompts/history.md`: record the prompt that initiated this session, per Constitution §VII
    step 0 ("a session without a recorded prompt did not happen").

---

## Definition of Done

- [ ] `query --run-id <existing>` and `ragas --run-id <existing>` both exit non-zero with a clear
      stderr message; no results are written or overwritten
- [ ] `query --run-id <new>` and `ragas --run-id <new>` both succeed, writing to
      `results/<new>/` exactly as `--run-id` already does today when passed directly to the CLI
- [ ] Omitting `--run-id` on either command reproduces today's auto-generated
      `{dataset}-{timestamp}` / `{dataset}-ragas-{timestamp}` id, byte-for-byte, including with a
      pre-existing unrelated `results/` directory present
- [ ] `_build_eval_command` appends `--run-id` for `query`/`ragas` only when non-empty; `download`
      and `ingest` commands are unaffected by the `run_id` parameter
- [ ] The Eval tab's `#eval-run-id` field (relabeled "Run Name") is sent as `runId` for `query`
      and `ragas`, in addition to its existing `metrics` use
- [ ] A collision or invalid-name error from the CLI is visible in the Eval tab's log box via the
      existing SSE error path, with no new client-side error handling
- [ ] A run started with a custom name appears under that name in Available Runs, the Metrics
      run dropdown, and Compare — with no code changes needed in those views (they already key
      off `run_id`/directory name)
- [ ] New/updated tests in `test_cli.py` and `test_routes.py` pass; existing tests unaffected
- [ ] `docs/wiki.md` updated if it documents Eval tab controls
- [ ] `prompts/history.md` updated with this session's initiating prompt
