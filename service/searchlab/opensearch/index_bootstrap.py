from opensearchpy import OpenSearch
from .. import config

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "chunk_text":      {"type": "text",    "analyzer": "standard"},
            "chunk_id":        {"type": "keyword"},
            "source_filename": {"type": "keyword"},
            "page_number":     {"type": "integer"},
            "chunk_position":  {"type": "integer"},
            "ingested_at":     {"type": "date"},
        }
    }
}


def ensure_index_exists(client: OpenSearch, index: str | None = None) -> None:
    name = index or config.index_name()
    if client.indices.exists(index=name):
        return
    client.indices.create(index=name, body=INDEX_MAPPING)
