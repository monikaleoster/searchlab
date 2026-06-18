import json
import sys
from pathlib import Path

import requests
from tqdm import tqdm


def run_query(query_text: str, searchlab_url: str, top_k: int, dataset: str) -> list[dict]:
    try:
        resp = requests.post(
            f"{searchlab_url}/api/query",
            data={"query": query_text, "topK": str(top_k), "dataset": dataset},
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"searchlab service unreachable at {searchlab_url}")
    if not resp.ok:
        raise RuntimeError(f"query failed HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return [
        {"doc_id": h["doc_id"], "score": h["score"], "rank": h["rank"]}
        for h in data.get("hits", [])
    ]


def load_queries(queries_path: Path) -> dict[str, str]:
    if not queries_path.exists():
        raise FileNotFoundError(f"Queries file not found: {queries_path}")
    queries = {}
    with open(queries_path) as fh:
        for line in fh:
            obj = json.loads(line)
            queries[obj["_id"]] = obj["text"]
    return queries


def run_queries(
    queries: dict[str, str],
    searchlab_url: str,
    top_k: int,
    dataset: str,
) -> dict[str, list[dict]]:
    results = {}
    for query_id, text in tqdm(queries.items(), desc="Querying", unit="q"):
        try:
            results[query_id] = run_query(text, searchlab_url, top_k, dataset)
        except RuntimeError as e:
            print(f"Warning: query {query_id!r} failed: {e}", file=sys.stderr)
            results[query_id] = []
    return results
