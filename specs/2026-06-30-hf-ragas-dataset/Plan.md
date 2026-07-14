# HuggingFace RAGAS Dataset: Implementation Plan

> **Architecture decision:** The existing `download` and `ragas` commands gain a HuggingFace
> branch, selected automatically when the dataset name contains `/`. The BEIR branch is
> unchanged. The `score()` function is shared by both branches — no duplication.

---


## Group 1 — Dependency Declaration

**Where:** `searchlab-eval/pyproject.toml`
    
1.1 Add `datasets` to the main `dependencies` list. It is a transitive dependency of `ragas`
    today but must be declared explicitly so it remains available if `ragas` changes its own
    dependency tree.

1.2 Run `uv sync` inside `searchlab-eval/` and confirm `from datasets import load_dataset`
    resolves without error.

---

## Group 2 — Detection Helper

**Where:** `searchlab-eval/searchlab_eval/dataset_utils.py` (new file)

2.1 Add `is_hf_dataset(name: str) -> bool` — returns `"/" in name`. Single source of truth
    used by both `download` and `ragas`.

2.2 Add `hf_data_dir(name: str) -> Path` — converts `vibrantlabsai/fiqa` to
    `data/vibrantlabsai-fiqa/` by replacing `/` with `-`. Used wherever a disk path is needed.

---

## Group 3 — HuggingFace Downloader

**Where:** `searchlab-eval/searchlab_eval/hf_downloader.py` (new file)

3.1 Implement `download_hf_dataset(hf_name: str, data_dir: Path) -> int`.
    - Calls `datasets.load_dataset(hf_name)`.
    - Auto-selects split: try `"baseline"`, then `"test"`, then first available split. Log
      which split was selected.
    - Iterates records and writes each as one JSON line to `data_dir/records.jsonl`:
      `{ "question": "...", "ground_truth": "...", "contexts": [...] }`.
    - Returns the total number of records written.

3.2 No slicing at download time — all records are written. Slicing happens at `ragas` time.

---

## Group 4 — `download` Command: HF Branch

**Where:** `searchlab-eval/searchlab_eval/cli.py`

4.1 In the existing `download` command, branch on `is_hf_dataset(dataset)`:

    ```python
    if is_hf_dataset(dataset):
        data_dir = hf_data_dir(dataset)
        data_dir.mkdir(parents=True, exist_ok=True)
        n = download_hf_dataset(dataset, data_dir)
        click.echo(f"Downloaded {dataset}: {n} records → {data_dir}/records.jsonl")
    else:
        # existing BEIR path — unchanged
        ...
    ```

4.2 The `--slice` flag is accepted but ignored for HF downloads, with a logged note
    (`--slice is applied at ragas time, not download time`).

---

## Group 5 — HF Record Loader

**Where:** `searchlab-eval/searchlab_eval/hf_downloader.py`

5.1 Implement `load_hf_records(data_dir: Path) -> list[dict]`.
    - Reads `data_dir/records.jsonl` line by line.
    - Returns list of `{ question, ground_truth, contexts }` dicts.
    - Raises `FileNotFoundError` with a message naming the missing file and the download
      command to run if `records.jsonl` does not exist.

5.2 Implement `slice_hf(records: list[dict], n: int) -> list[dict]`.
    - Returns first `n` records deterministically (list order = HF dataset order).
    - If `n == 0`, returns all records.

---

## Group 6 — Generation Step for HF (system mode)

**Where:** `searchlab-eval/searchlab_eval/rag_eval.py`

6.1 Add `generate_from_hf(records: list[dict], dataset: str, searchlab_url: str, top_k: int = 10) -> list[dict]`.
    - For each record, POST to `{searchlab_url}/rag` with `question`, `topK`, `dataset`.
    - Resolves retrieved passage text from `sources[].filename` using `_load_corpus()` (already
      exists in `rag_eval.py`). The BEIR FiQA corpus directory is derived from the base dataset
      name (strip the `org/` prefix: `vibrantlabsai/fiqa` → look for `data/fiqa/corpus.jsonl`).
    - Populates `ground_truth` directly from the HF record — no qrel cross-reference.
    - `query_id` is the record's zero-padded positional index (`"0000"`, `"0001"`, …).
    - Returns the same per-query dict shape as `generate()`:
      `{ query_id, question, contexts, answer, ground_truth }`.

6.2 Error handling mirrors `generate()`:
    - `ConnectionError` → clear message, exit 1.
    - Per-query timeout or HTTP error → log and skip; batch continues.
    - `OPENAI_API_KEY` missing error in response → clear message, exit 0.

---

## Group 7 — `ragas` Command: HF Branch

**Where:** `searchlab-eval/searchlab_eval/cli.py`

7.1 In the existing `ragas_cmd`, branch on `is_hf_dataset(dataset)` after the run ID is set:

    ```python
    if is_hf_dataset(dataset):
        records = load_hf_records(hf_data_dir(dataset))   # raises if missing
        if slice_n > 0:
            records = slice_hf(records, slice_n)
        results = generate_from_hf(records, dataset, searchlab_url)
    else:
        # existing BEIR path — unchanged
        queries = load_queries(queries_path)
        ...
        results = generate(queries, data_dir, dataset, searchlab_url)
    ```

7.2 `score()` is called identically in both branches — no changes to scoring.

7.3 Run ID for HF datasets defaults to `{safe_name}-ragas-{timestamp}` where `safe_name`
    replaces `/` with `-` (e.g., `vibrantlabsai-fiqa-ragas-20260630T120000Z`).

7.4 HF datasets always run all four RAGAS metrics — `ground_truth` is always present.
    The existing conditional metric selection (skipped for nfcorpus) is in the BEIR branch
    only; no change needed there.

7.5 Missing `records.jsonl` (download not run) surfaces as a clear CLI error:
    `Error: records not found at data/vibrantlabsai-fiqa/records.jsonl — run download first`.

---

## Group 8 — Output Files

**Where:** `results/<run_id>/`

8.1 `rag_results.json` — identical schema to Phase 2. Add a top-level `"source": "hf"` field
    so runs are self-describing when browsed manually.

8.2 `rag_scores.json` — identical schema to Phase 2. No changes to the Metrics tab required.

---

## Group 9 — README & Documentation

**Where:** `docs/wiki.md`

9.1 Document the full HF dataset flow:

    ```bash
    # 1. Download HF dataset
    searchlab-eval download --dataset vibrantlabsai/fiqa

    # 2. Ingest BEIR FiQA corpus into OpenSearch (prerequisite — same corpus, different source)
    searchlab-eval ingest --dataset fiqa

    # 3. Run RAGAS evaluation
    searchlab-eval ragas --dataset vibrantlabsai/fiqa --slice 50
    ```

9.2 Explain the `/` detection rule in one sentence so users know they can pass any
    HuggingFace `org/dataset` name.

9.3 Note that `--slice` on `download` is ignored for HF datasets; slicing happens at `ragas`
    time.

9.4 Add a new benchmark row `HF FiQA (system)` to the results table once a real run produces
    scores.