# HuggingFace RAGAS Dataset (`vibrantlabsai/fiqa`): Requirements

## Context

Phase 2 wired RAGAS into `searchlab-eval` using the BEIR FiQA corpus as the evaluation dataset.
Ground truth for FiQA was derived indirectly: the highest-scored `qrels` document's passage text
was used as the reference answer. This is a structural limitation — a retrieved passage is not
the same thing as a curated reference answer, and RAGAS metrics that depend on `ground_truth`
(`context_recall`, `context_precision`) are measured against an approximation.

The HuggingFace dataset `vibrantlabsai/fiqa` is a RAGAS-formatted testset with curated
`(question, ground_truth)` pairs where `ground_truth` is the actual expected answer — not a
retrieved passage. Using this dataset as the ground truth source produces more meaningful
context recall and context precision scores.

---

## Objective

Extend the existing `download` and `ragas` commands to support HuggingFace datasets alongside
BEIR datasets. The two are distinguished by dataset name format: a `/` in the name signals a
HuggingFace dataset (`vibrantlabsai/fiqa`); no `/` signals BEIR (`fiqa`).

The flow mirrors the existing BEIR pipeline — download first, evaluate later, everything on
disk — so the interface and mental model are unchanged for the user.

This produces a new benchmark row comparable to the Phase 2 BEIR-derived RAGAS row, with
higher-quality ground truth. The two rows together let us separate retrieval quality from
ground-truth quality as sources of metric variance.

**No changes to the RAG pipeline.** `RagCommand`, `ContextBuilder`, and `LlmClient` are
measured as-is.

---

## Scope Decisions

### Dataset name as the discriminator

| Dataset name | Contains `/`? | Path taken |
|---|---|---|
| `fiqa` | No | BEIR — existing behaviour, unchanged |
| `nfcorpus` | No | BEIR — existing behaviour, unchanged |
| `vibrantlabsai/fiqa` | Yes | HuggingFace — new path |

The check is a single `"/" in dataset` condition applied in both `download` and `ragas`. No new
flags are needed for the common case.

### Download before evaluate (no network calls at eval time)

HF datasets are downloaded once via `searchlab-eval download` and saved to disk as
`data/<safe-name>/records.jsonl`. The `ragas` command reads from that file — it never calls
`datasets.load_dataset()` at eval time. This follows the Constitution's "no magic" principle:
every intermediate artifact is on disk, inspectable, and reproducible without re-hitting the
network.

Safe directory name: replace `/` with `-` → `vibrantlabsai/fiqa` → `data/vibrantlabsai-fiqa/`.

### On-disk layout for HF datasets

```
data/
  fiqa/                        # BEIR layout — unchanged
    corpus.jsonl
    queries.jsonl
    qrels/test.tsv

  vibrantlabsai-fiqa/          # HF layout — new
    records.jsonl              # one JSON object per line: {question, ground_truth, contexts}
```

`records.jsonl` stores all records from the HF dataset. Slicing happens at `ragas` time via
`--slice`, not at download time. This keeps the downloaded artifact complete and reusable across
different slice sizes.

### Corpus ingest prerequisite for HF `ragas`

The `/rag` endpoint needs something in OpenSearch to retrieve from. The FiQA BEIR corpus is the
same underlying document collection. The BEIR FiQA corpus must be ingested before running
`ragas --dataset vibrantlabsai/fiqa`. This is a documented prerequisite, not a hidden dependency.

### Slice size

Default 50 queries, matching the Phase 2 RAGAS default. Controlled by `--slice`. Applied at
`ragas` time from the full `records.jsonl`.

### Dataset dependency

`datasets` (HuggingFace) is already a transitive dependency of `ragas`. It must be declared
explicitly in `pyproject.toml` so the import is guaranteed even if `ragas` changes its own
dependency tree.

---

## Functional Requirements

| # | Requirement |
|---|-------------|
| F1 | `searchlab-eval download --dataset vibrantlabsai/fiqa` fetches the HF dataset and writes all records to `data/vibrantlabsai-fiqa/records.jsonl`. |
| F2 | `searchlab-eval ragas --dataset vibrantlabsai/fiqa --slice 50` reads from `data/vibrantlabsai-fiqa/records.jsonl`, makes no network call to HuggingFace, queries `/rag` per question, and produces `rag_results.json` and `rag_scores.json`. |
| F3 | Dataset type is detected automatically: `"/" in dataset` → HF path; else → BEIR path. No new flags required. |
| F4 | `rag_results.json` schema is identical to the Phase 2 schema: `{ query_id, question, contexts, answer, ground_truth }` per query. |
| F5 | `rag_scores.json` schema is identical to Phase 2: `{ aggregate, per_query, measures, judge_model }`. |
| F6 | All four RAGAS metrics are computed for HF datasets; `ground_truth` is always populated from `records.jsonl` (never null, never qrel-derived). |
| F7 | Missing `OPENAI_API_KEY` produces a clear message and exits 0 with no stack trace. |
| F8 | A single query failure is logged and excluded from the aggregate; the batch does not abort. |
| F9 | `ragas --dataset vibrantlabsai/fiqa` run before `download` produces a clear error naming the missing file and the command to run. |

---

## Out of Scope

| Item | Notes |
|------|-------|
| Offline scoring mode | Removed — only system eval (query our `/rag`) is supported |
| Modifying the existing BEIR `ragas` path | Unchanged; HF and BEIR are separate code branches inside the same command |
| Automatic BEIR corpus ingest | Prerequisite, not in scope; documented in README |
| HF datasets other than `vibrantlabsai/fiqa` | Detection works for any `org/name` format but only this dataset is tested and benchmarked |
| Changes to retrieval, prompts, or scoring logic | Measurement only; pipeline unchanged |
| HTML report changes | Existing report renders `rag_scores.json` correctly; no new UI work required |