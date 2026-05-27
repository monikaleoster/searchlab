import json
import os
import re
import subprocess
import sys
from pathlib import Path

from tqdm import tqdm

HIT_RE = re.compile(r'^(\d+)\s+([\d.]+)\s+(\S+)\s+(\d+)\s+(.*)$')


def _parse_hits(stdout: str) -> list[dict]:
    hits = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        if line.startswith("Rank") or line.startswith("---"):
            continue
        if line.startswith("No results found for:"):
            return []
        m = HIT_RE.match(line)
        if m:
            hits.append({"doc_id": m.group(3), "score": float(m.group(2)), "rank": int(m.group(1))})
    return hits


def run_query(query_text: str, opensearch_url: str, top_k: int) -> list[dict]:
    cmd = ["searchlab", "query", query_text, "--top-k", str(top_k)]
    env = {**os.environ, "OPENSEARCH_URL": opensearch_url}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"searchlab query exited {proc.returncode}: {proc.stderr.strip()}")
    return _parse_hits(proc.stdout)


def load_queries(queries_path: Path) -> dict[str, str]:
    if not queries_path.exists():
        raise FileNotFoundError(f"Queries file not found: {queries_path}")
    queries = {}
    with open(queries_path) as fh:
        for line in fh:
            obj = json.loads(line)
            queries[obj["_id"]] = obj["text"]
    return queries


def run_queries(queries: dict[str, str], opensearch_url: str, top_k: int) -> dict[str, list[dict]]:
    results = {}
    for query_id, text in tqdm(queries.items(), desc="Querying", unit="q"):
        try:
            results[query_id] = run_query(text, opensearch_url, top_k)
        except RuntimeError as e:
            print(f"Warning: query {query_id!r} failed: {e}", file=sys.stderr)
            results[query_id] = []
    return results
