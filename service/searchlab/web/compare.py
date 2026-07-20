"""Per-query comparison of two eval runs of the same type (IR or RAG).

Read-only: builds comparison rows from the JSON files the eval harness already
writes (`ir_scores.json`, `rag_scores.json`, `rag_results.json`, `raw_results.json`).
Nothing is written to disk and no eval-harness output schema is touched.
"""

import json
from pathlib import Path

# service/searchlab/web/compare.py → service/searchlab/web/ → service/searchlab/ → service/ → repo root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_RESULTS_DIR = _REPO_ROOT / "searchlab-eval" / "results"
_DATA_DIR = _REPO_ROOT / "searchlab-eval" / "data"


def _run_dir(run_id: str) -> Path:
    return _RESULTS_DIR / run_id


def _load_queries(dataset: str) -> dict[str, str]:
    """query_id -> text, from the dataset's BEIR queries.jsonl. Empty dict if missing."""
    path = _DATA_DIR / dataset / "queries.jsonl"
    if not path.exists():
        return {}
    queries: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        queries[entry["_id"]] = entry.get("text")
    return queries


def load_qrels(dataset: str, query_id: str) -> list[dict]:
    """Reads [{doc_id, score}, ...] for query_id from the dataset's BEIR qrels/test.tsv.

    A query with zero judged docs is a valid data state, not an error: returns [].
    """
    path = _DATA_DIR / dataset / "qrels" / "test.tsv"
    if not path.exists():
        raise FileNotFoundError(f"Dataset '{dataset}' has no qrels/test.tsv")
    judgements = []
    lines = path.read_text().splitlines()
    for line in lines[1:]:  # skip header row (query-id, corpus-id, score)
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        qid, doc_id, score = parts[0], parts[1], parts[2]
        if qid == query_id:
            judgements.append({"doc_id": doc_id, "score": int(score)})
    return judgements


def load_document(dataset: str, doc_id: str) -> dict:
    """Reads {doc_id, title, text} for doc_id from the dataset's BEIR corpus.jsonl."""
    path = _DATA_DIR / dataset / "corpus.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Dataset '{dataset}' has no corpus.jsonl")
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        if entry.get("_id") == doc_id:
            return {"doc_id": doc_id, "title": entry.get("title", ""), "text": entry.get("text", "")}
    raise FileNotFoundError(f"Document '{doc_id}' not found in dataset '{dataset}'")


def _load_json(run_id: str, filename: str, type_label: str) -> dict:
    path = _run_dir(run_id) / filename
    if not path.exists():
        raise FileNotFoundError(f"Run '{run_id}' is not a {type_label} run (missing {filename})")
    return json.loads(path.read_text())


def load_ir_scores(run_id: str) -> dict:
    return _load_json(run_id, "ir_scores.json", "IR eval")


def load_rag_scores(run_id: str) -> dict:
    return _load_json(run_id, "rag_scores.json", "RAG eval")


def load_rag_results(run_id: str) -> dict:
    return _load_json(run_id, "rag_results.json", "RAG eval")


def load_raw_results(run_id: str) -> dict | None:
    path = _run_dir(run_id) / "raw_results.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _shared_measures(scores_a: dict, scores_b: dict) -> list[str]:
    measures_b = set(scores_b.get("measures", []))
    return [m for m in scores_a.get("measures", []) if m in measures_b]


def _check_same_dataset(run_a: str, run_b: str, scores_a: dict, scores_b: dict) -> str:
    dataset_a = scores_a.get("dataset", "")
    dataset_b = scores_b.get("dataset", "")
    if dataset_a != dataset_b:
        raise ValueError(
            f"Dataset mismatch: '{run_a}' is dataset '{dataset_a}', "
            f"'{run_b}' is dataset '{dataset_b}'"
        )
    return dataset_a


def _metric_subset(metrics: dict, measures: list[str]) -> dict:
    return {m: metrics.get(m) for m in measures}


def _delta(a_metrics: dict, b_metrics: dict, measures: list[str]) -> dict:
    return {
        m: b_metrics[m] - a_metrics[m]
        for m in measures
        if a_metrics.get(m) is not None and b_metrics.get(m) is not None
    }


def _zero_counts(per_query: dict, measures: list[str]) -> dict:
    return {
        m: sum(1 for entry in per_query.values() if entry.get(m) == 0)
        for m in measures
    }


def compare_ir(run_a: str, run_b: str) -> dict:
    scores_a = load_ir_scores(run_a)
    scores_b = load_ir_scores(run_b)
    dataset = _check_same_dataset(run_a, run_b, scores_a, scores_b)
    measures = _shared_measures(scores_a, scores_b)
    aggregate_a = _metric_subset(scores_a.get("aggregate", {}), measures)
    aggregate_b = _metric_subset(scores_b.get("aggregate", {}), measures)
    aggregate_delta = _delta(aggregate_a, aggregate_b, measures)

    pq_a = scores_a.get("per_query", {})
    pq_b = scores_b.get("per_query", {})
    zero_counts_a = _zero_counts(pq_a, measures)
    zero_counts_b = _zero_counts(pq_b, measures)

    raw_a = load_raw_results(run_a)
    raw_b = load_raw_results(run_b)
    sources_a = (raw_a or {}).get("results", {})
    sources_b = (raw_b or {}).get("results", {})
    queries = _load_queries(dataset)

    rows = []
    for qid, a_raw in pq_a.items():
        if qid not in pq_b:
            continue
        b_raw = pq_b[qid]
        a_metrics = _metric_subset(a_raw, measures)
        b_metrics = _metric_subset(b_raw, measures)
        rows.append({
            "query_id": qid,
            "query_text": queries.get(qid),
            "a": a_metrics,
            "b": b_metrics,
            "delta": _delta(a_metrics, b_metrics, measures),
            "sources_a": sources_a.get(qid),
            "sources_b": sources_b.get(qid),
        })

    only_in_a = [
        {
            "query_id": qid,
            "query_text": queries.get(qid),
            "a": _metric_subset(pq_a[qid], measures),
            "sources_a": sources_a.get(qid),
        }
        for qid in sorted(set(pq_a) - set(pq_b))
    ]
    only_in_b = [
        {
            "query_id": qid,
            "query_text": queries.get(qid),
            "b": _metric_subset(pq_b[qid], measures),
            "sources_b": sources_b.get(qid),
        }
        for qid in sorted(set(pq_b) - set(pq_a))
    ]

    return {
        "run_a": run_a,
        "run_b": run_b,
        "dataset": dataset,
        "measures": measures,
        "aggregate_a": aggregate_a,
        "aggregate_b": aggregate_b,
        "aggregate_delta": aggregate_delta,
        "zero_counts_a": zero_counts_a,
        "zero_counts_b": zero_counts_b,
        "rows": rows,
        "only_in_a": only_in_a,
        "only_in_b": only_in_b,
    }


def compare_rag(run_a: str, run_b: str) -> dict:
    scores_a = load_rag_scores(run_a)
    scores_b = load_rag_scores(run_b)
    dataset = _check_same_dataset(run_a, run_b, scores_a, scores_b)
    measures = _shared_measures(scores_a, scores_b)
    aggregate_a = _metric_subset(scores_a.get("aggregate", {}), measures)
    aggregate_b = _metric_subset(scores_b.get("aggregate", {}), measures)
    aggregate_delta = _delta(aggregate_a, aggregate_b, measures)

    pq_a = scores_a.get("per_query", {})
    pq_b = scores_b.get("per_query", {})
    zero_counts_a = _zero_counts(pq_a, measures)
    zero_counts_b = _zero_counts(pq_b, measures)
    results_a = load_rag_results(run_a).get("per_query", [])
    results_b = load_rag_results(run_b).get("per_query", [])

    n = min(len(results_a), len(results_b))

    rows = []
    for i in range(n):
        key = str(i)
        a_metrics = _metric_subset(pq_a.get(key, {}), measures)
        b_metrics = _metric_subset(pq_b.get(key, {}), measures)
        question_a = results_a[i].get("question")
        question_b = results_b[i].get("question")
        ground_truth_a = results_a[i].get("ground_truth")
        ground_truth_b = results_b[i].get("ground_truth")
        row = {
            "index": i,
            "query_id": results_a[i].get("query_id"),
            "query_text": question_a,
            "ground_truth": ground_truth_a,
            "a": a_metrics,
            "b": b_metrics,
            "delta": _delta(a_metrics, b_metrics, measures),
            "content_a": results_a[i],
            "content_b": results_b[i],
        }
        if question_a != question_b:
            row["query_text_mismatch"] = True
        if ground_truth_a != ground_truth_b:
            row["ground_truth_mismatch"] = True
        rows.append(row)

    only_in_a = [
        {
            "index": i,
            "query_id": results_a[i].get("query_id"),
            "query_text": results_a[i].get("question"),
            "a": _metric_subset(pq_a.get(str(i), {}), measures),
            "content_a": results_a[i],
        }
        for i in range(n, len(results_a))
    ]
    only_in_b = [
        {
            "index": i,
            "query_id": results_b[i].get("query_id"),
            "query_text": results_b[i].get("question"),
            "b": _metric_subset(pq_b.get(str(i), {}), measures),
            "content_b": results_b[i],
        }
        for i in range(n, len(results_b))
    ]

    return {
        "run_a": run_a,
        "run_b": run_b,
        "dataset": dataset,
        "measures": measures,
        "aggregate_a": aggregate_a,
        "aggregate_b": aggregate_b,
        "aggregate_delta": aggregate_delta,
        "zero_counts_a": zero_counts_a,
        "zero_counts_b": zero_counts_b,
        "rows": rows,
        "only_in_a": only_in_a,
        "only_in_b": only_in_b,
    }
