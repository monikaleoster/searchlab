# Custom Run Name: Validation

> Per the Constitution (Section VII), a phase is not complete because the code works.
> Every criterion below must pass before this work is merged.

---

## Acceptance Criteria

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| AC1 | `searchlab-eval query --dataset <d> --run-id <name>` succeeds when `results/<name>/` doesn't already exist | `results/<name>/raw_results.json` written; exit code 0 | Wrong directory used, crash, or non-zero exit |
| AC2 | `searchlab-eval query --dataset <d> --run-id <name>` fails when `results/<name>/` already exists | Non-zero exit, clear stderr message naming `<name>`; existing `results/<name>/` contents untouched | Silent overwrite, crash with a stack trace, or a misleading error |
| AC3 | `searchlab-eval ragas --dataset <d> --run-id <name>` succeeds when `results/<name>/` doesn't already exist | `results/<name>/rag_results.json` (and `rag_scores.json` after scoring) written; exit code 0 | Wrong directory, crash, or non-zero exit |
| AC4 | `searchlab-eval ragas --dataset <d> --run-id <name>` fails when `results/<name>/` already exists | Non-zero exit, clear stderr message naming `<name>`; existing contents untouched | Silent overwrite, crash, or misleading error |
| AC5 | Omitting `--run-id` on `query` reproduces today's auto-generated id | `results/<dataset>-<timestamp>/` created, same format as before this change | Format changed, or collision check incorrectly fires on the auto-generated path |
| AC6 | Omitting `--run-id` on `ragas` reproduces today's auto-generated id | `results/<dataset>-ragas-<timestamp>/` created, same format as before this change | Format changed, or collision check incorrectly fires |
| AC7 | `_build_eval_command("query", dataset, run_id="run1")` includes `--run-id run1` | `--run-id` and `run1` present, in that order, after `--dataset <dataset>` | Missing, wrong position, or wrong value |
| AC8 | `_build_eval_command("query", dataset)` (no `run_id`) omits `--run-id` entirely | Command identical to pre-change output | Extra/empty `--run-id` flag present |
| AC9 | `_build_eval_command("ragas", dataset, run_id="run1")` includes `--run-id run1` | Present, correctly positioned | Missing or wrong value |
| AC10 | `_build_eval_command("ragas", dataset)` (no `run_id`) omits `--run-id` entirely | Command identical to pre-change output | Extra/empty flag present |
| AC11 | `_build_eval_command("ingest", ...)` and `_build_eval_command("download", ...)` are unaffected by a passed `run_id` | Commands identical with or without `run_id` set | `--run-id` incorrectly appears on either op |
| AC12 | Eval tab's Run Name field is sent as `runId` when starting Query or RAG Eval with a non-blank value | Request URL to `/api/eval/stream` includes `&runId=<value>` | Field ignored for these ops |
| AC13 | Eval tab's Run Name field left blank when starting Query or RAG Eval doesn't send `runId` | Request URL has no `runId` param (or empty), CLI auto-generates as before | Empty `runId=` sent and mishandled, or default behavior altered |
| AC14 | A collision error from the CLI is visible in the Eval tab's log box | Log box shows the stderr error line; `event: error` fires; run buttons re-enable | Error swallowed, blank log, or UI stuck in a running state |
| AC15 | A successfully custom-named run appears under that name in Available Runs, Metrics run dropdown, and Compare | All three surfaces list the custom name with correct metadata (dataset, computedAt where applicable) | Run missing from a list, or shown under a different id |
| AC16 | Metrics op's existing required-`runId` behavior is unchanged | Running `Compute Metrics` with the field blank still errors "runId is required for metrics" (400/inline), exactly as before this change | Behavior regressed (e.g. silently no-ops, or crashes) |

---

## Manual Verification

### 1. Set up

```bash
docker compose up -d
cd service && uv run searchlab serve
```
In another terminal, ensure `nfcorpus` is downloaded (Eval tab → Dataset `nfcorpus` → Download, if
not already local).

### 2. Query with a custom run name — happy path

- Eval tab: set Dataset to `nfcorpus`, type `bm25-baseline` in the Run Name field, click **Query**.

Check:
- Log shows `$ uv run searchlab-eval query --dataset nfcorpus --run-id bm25-baseline`.
- Completes successfully; `searchlab-eval/results/bm25-baseline/raw_results.json` exists.
- Available Runs (refresh) shows `bm25-baseline` in the list.

### 3. Query with a colliding run name — rejected

- With Run Name still set to `bm25-baseline`, click **Query** again.

Check:
- Log shows a clear error naming `bm25-baseline` (e.g. "run 'bm25-baseline' already exists");
  process exits non-zero; UI shows the error state, buttons re-enable.
- `results/bm25-baseline/raw_results.json`'s contents/mtime are unchanged (not overwritten).

### 4. Query with the field left blank — unchanged default behavior

- Clear the Run Name field, click **Query**.

Check:
- Log shows `$ uv run searchlab-eval query --dataset nfcorpus` with **no** `--run-id` flag.
- Completes successfully; a new `results/nfcorpus-<timestamp>/` directory appears, same format as
  before this feature existed.

### 5. RAG Eval (ragas) with a custom run name — happy path

Requires `OPENAI_API_KEY` set.

- Set Run Name to `ragas-baseline`, click **RAG Eval**.

Check:
- Log shows `--run-id ragas-baseline` in the invoked command.
- `results/ragas-baseline/rag_results.json` produced; Available Runs shows it.

### 6. RAG Eval with a colliding run name — rejected

- With Run Name still `ragas-baseline`, click **RAG Eval** again.

Check: clear error naming the conflict; no partial/overwritten files in `results/ragas-baseline/`.

### 7. Metrics still requires a run name (unchanged)

- Clear Run Name, click **Compute Metrics**.

Check: same "runId is required" error as before this change — behavior unaffected.

### 8. Named run flows through Metrics and Compare

- Set Run Name to `bm25-baseline`, click **Compute Metrics**.

Check: metrics compute successfully and display under the run name `bm25-baseline`; switching to
the Compare tab and selecting `bm25-baseline` as one of the two runs works exactly as it does for
any auto-generated run id today.

---

## Merge Checklist

> A phase is done or it is in progress. There is no "almost done." — Constitution § X

- [ ] AC1–AC16 all pass.
- [ ] Manual verification steps 1–8 completed; pass/fail noted for each.
- [ ] `query`'s collision guard covered by unit tests: collision rejected, new name succeeds,
      auto-generated path unaffected by a pre-existing unrelated `results/` entry.
- [ ] `ragas`'s collision guard covered by the same three cases.
- [ ] `_build_eval_command`'s `run_id` handling for `query`/`ragas` covered by unit tests
      (appends when given, omits when blank); `ingest`/`download` confirmed unaffected.
- [ ] No changes to `metrics`'s existing required-`runId` behavior.
- [ ] No changes to `run_id` format or content for the omitted-flag (auto-generated) path on
      either `query` or `ragas`.
- [ ] `docs/wiki.md` updated if it documents Eval tab controls.
- [ ] `prompts/history.md` updated with the prompt that initiated this session (Constitution
      § VII step 0).
