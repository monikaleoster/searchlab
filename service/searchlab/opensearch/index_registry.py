"""File-backed registry of indexes created through the Indexes tab.

Mirrors how `searchlab-eval/results/` records eval runs: a lazily-created,
git-ignored JSON file under `service/searchlab/data/`. An empty/missing file
is the normal first-run state, not an error.
"""

import json
import os
from pathlib import Path

# service/searchlab/opensearch/index_registry.py → opensearch/ → searchlab/ → service/ → repo root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_REGISTRY_PATH = _REPO_ROOT / "service" / "searchlab" / "data" / "index_registry.json"


def load_registry() -> list[dict]:
    if not _REGISTRY_PATH.exists():
        return []
    return json.loads(_REGISTRY_PATH.read_text())


def save_entry(entry: dict) -> None:
    entries = load_registry()
    entries.append(entry)
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _REGISTRY_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(entries, indent=2))
    os.replace(tmp_path, _REGISTRY_PATH)


def find_by_key(key: str) -> dict | None:
    for entry in load_registry():
        if entry["key"] == key:
            return entry
    return None


def find_by_index(index_name: str) -> dict | None:
    for entry in load_registry():
        if entry["index"] == index_name:
            return entry
    return None


def key_exists(key: str) -> bool:
    return find_by_key(key) is not None
