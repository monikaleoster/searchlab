"""Index creation/listing logic behind the Indexes tab.

Mirrors how `web/compare.py` holds all comparison logic behind the
`/api/eval/compare` route: routes.py stays a thin HTTP layer, this module
holds the actual behavior.
"""

import re

from opensearchpy import OpenSearch

from . import index_registry

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

# Built-in dataset keys (DATASET_INDEX plus "default") a custom index must not shadow.
_RESERVED_KEYS = {"default", "nfcorpus", "fiqa"}


def validate_key(key: str) -> None:
    if not key:
        raise ValueError("Index name is required.")
    if key in _RESERVED_KEYS:
        raise ValueError(f"'{key}' is a reserved name and can't be used for a custom index.")
    if not _NAME_RE.match(key):
        raise ValueError(
            "Index name must start with a lowercase letter or digit and contain only "
            "lowercase letters, digits, and hyphens (max 63 characters)."
        )


def create_index(client: OpenSearch, key: str, schema_body: dict) -> str:
    validate_key(key)
    full_name = f"searchlab-{key}"
    if client.indices.exists(index=full_name) or index_registry.key_exists(key):
        raise ValueError(f"Index '{full_name}' already exists.")
    client.indices.create(index=full_name, body=schema_body)
    return full_name


def list_indexes(client: OpenSearch) -> list[dict]:
    cat_entries = client.cat.indices(index="searchlab-*", format="json", h="index,docs.count")
    entries = []
    for row in cat_entries:
        index_name = row["index"]
        doc_count = int(row.get("docs.count") or 0)
        registry_entry = index_registry.find_by_index(index_name)
        if registry_entry:
            entries.append({
                "index": index_name,
                "label": registry_entry["label"],
                "docCount": doc_count,
                "schemaSource": registry_entry["schemaSource"],
                "createdAt": registry_entry["createdAt"],
            })
        else:
            entries.append({
                "index": index_name,
                "label": index_name,
                "docCount": doc_count,
                "schemaSource": "pre-existing",
                "createdAt": None,
            })
    return sorted(entries, key=lambda e: e["index"])
