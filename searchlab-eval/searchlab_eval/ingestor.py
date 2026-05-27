import json
from datetime import datetime, timezone
from pathlib import Path

import requests


def _build_bulk_body(docs: list[dict], ingested_at: str) -> str:
    lines: list[str] = []
    for doc in docs:
        doc_id = doc["_id"]
        lines.append(json.dumps({"index": {"_index": "searchlab-v0", "_id": doc_id}}))
        lines.append(json.dumps({
            "chunk_id": doc_id,
            "chunk_text": doc["title"] + " " + doc["text"],
            "source_filename": doc_id,
            "page_number": 0,
            "chunk_position": 0,
            "ingested_at": ingested_at,
        }))
    return "\n".join(lines) + "\n"


def _post_bulk(opensearch_url: str, body: str) -> None:
    try:
        resp = requests.post(
            f"{opensearch_url}/_bulk",
            data=body,
            headers={"Content-Type": "application/x-ndjson"},
            timeout=60,
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"OpenSearch unreachable at {opensearch_url}")

    if not resp.ok:
        raise RuntimeError(
            f"Bulk request failed with HTTP {resp.status_code}: {resp.text[:200]}"
        )

    payload = resp.json()
    if payload.get("errors"):
        for item in payload.get("items", []):
            op = item.get("index") or item.get("create") or {}
            if "error" in op:
                reason = op["error"].get("reason", "unknown error")
                raise RuntimeError(f"Bulk index error: {reason}")
        raise RuntimeError("Bulk request returned errors=true")


def ingest_corpus(corpus_path: Path, opensearch_url: str, batch_size: int = 500) -> int:
    corpus_path = Path(corpus_path)
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus not found: {corpus_path}")

    ingested_at = datetime.now(timezone.utc).isoformat()
    total = 0
    batch: list[dict] = []

    with corpus_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            batch.append(json.loads(line))
            if len(batch) >= batch_size:
                _post_bulk(opensearch_url, _build_bulk_body(batch, ingested_at))
                total += len(batch)
                batch = []

    if batch:
        _post_bulk(opensearch_url, _build_bulk_body(batch, ingested_at))
        total += len(batch)

    return total


def get_doc_count(opensearch_url: str, index: str = "searchlab-v0") -> int:
    try:
        resp = requests.get(f"{opensearch_url}/{index}/_count", timeout=10)
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"OpenSearch unreachable at {opensearch_url}")

    if not resp.ok:
        raise RuntimeError(
            f"Count request failed with HTTP {resp.status_code}: {resp.text[:200]}"
        )

    return resp.json()["count"]
