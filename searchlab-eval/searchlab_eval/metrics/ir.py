import csv
import json
from pathlib import Path

import pytrec_eval

MEASURES = {
    "ndcg_cut_1",
    "ndcg_cut_3",
    "ndcg_cut_5",
    "ndcg_cut_10",
    "map_cut_10",
    "recall_5",
    "recall_10",
}

_DISPLAY_ORDER = [
    "ndcg_cut_1",
    "ndcg_cut_3",
    "ndcg_cut_5",
    "ndcg_cut_10",
    "map_cut_10",
    "recall_5",
    "recall_10",
]


def load_run(run_path: Path) -> tuple[str, str, dict[str, list[dict]]]:
    if not run_path.exists():
        raise FileNotFoundError(run_path)
    data = json.loads(run_path.read_text())
    return data["run_id"], data["dataset"], data["results"]


def load_qrels(qrels_path: Path) -> dict[str, dict[str, int]]:
    if not qrels_path.exists():
        raise FileNotFoundError(qrels_path)
    qrels: dict[str, dict[str, int]] = {}
    with open(qrels_path, newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        next(reader)  # skip header
        for row in reader:
            query_id, doc_id, score = row[0], row[1], row[2]
            qrels.setdefault(query_id, {})[doc_id] = int(score)
    return qrels


def build_pytrec_run(results: dict[str, list[dict]]) -> dict[str, dict[str, float]]:
    return {
        query_id: {hit["doc_id"]: hit["score"] for hit in hits}
        for query_id, hits in results.items()
    }


def compute_metrics(
    run: dict[str, dict[str, float]],
    qrels: dict[str, dict[str, int]],
) -> dict[str, dict[str, float]]:
    evaluator = pytrec_eval.RelevanceEvaluator(qrels, MEASURES)
    return evaluator.evaluate(run)


def aggregate(per_query: dict[str, dict[str, float]]) -> dict[str, float]:
    n = len(per_query)
    if n == 0:
        return {m: 0.0 for m in sorted(MEASURES)}
    return {
        measure: sum(scores.get(measure, 0.0) for scores in per_query.values()) / n
        for measure in sorted(MEASURES)
    }


def format_table(agg: dict[str, float]) -> str:
    lines = [
        f"{'Metric':<16}  {'Score':>7}",
        f"{'-' * 16}  {'-' * 7}",
    ]
    for measure in _DISPLAY_ORDER:
        lines.append(f"{measure:<16}  {agg.get(measure, 0.0):>7.4f}")
    return "\n".join(lines)
