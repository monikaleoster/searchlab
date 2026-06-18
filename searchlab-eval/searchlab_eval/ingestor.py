import json
from pathlib import Path

import requests


def ingest_corpus(corpus_path: Path, searchlab_url: str, index: str, batch_size: int = 500) -> int:
    corpus_path = Path(corpus_path)
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus not found: {corpus_path}")

    total = 0
    batch: list[dict] = []

    def _flush(batch_docs: list[dict]) -> int:
        try:
            resp = requests.post(
                f"{searchlab_url}/api/corpus-ingest",
                params={"index": index},
                json=batch_docs,
                timeout=120,
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"searchlab service unreachable at {searchlab_url}")
        if not resp.ok:
            raise RuntimeError(f"corpus-ingest failed HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"corpus-ingest error: {data['error']}")
        return data.get("indexed", len(batch_docs))

    with corpus_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            batch.append(json.loads(line))
            if len(batch) >= batch_size:
                total += _flush(batch)
                batch = []

    if batch:
        total += _flush(batch)

    return total
