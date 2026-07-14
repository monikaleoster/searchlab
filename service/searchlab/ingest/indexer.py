from datetime import datetime, timezone

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from .chunker import Chunk


def index_chunks(client: OpenSearch, chunks: list[Chunk], source_filename: str, index: str) -> int:
    ingested_at = datetime.now(timezone.utc).isoformat()
    actions = [
        {
            "_index": index,
            "_id": f"{source_filename}_{chunk.position}",
            "_source": {
                "chunk_id": f"{source_filename}_{chunk.position}",
                "chunk_text": chunk.text,
                "source_filename": source_filename,
                "page_number": chunk.page_number,
                "chunk_position": chunk.position,
                "ingested_at": ingested_at,
            },
        }
        for chunk in chunks
    ]
    success, _ = bulk(client, actions)
    return success


def index_corpus_docs(client: OpenSearch, docs: list[dict], index: str) -> int:
    ingested_at = datetime.now(timezone.utc).isoformat()
    actions = [
        {
            "_index": index,
            "_id": doc["_id"],
            "_source": {
                "chunk_id": doc["_id"],
                "chunk_text": doc["title"] + " " + doc["text"],
                "source_filename": doc["_id"],
                "page_number": 0,
                "chunk_position": 0,
                "ingested_at": ingested_at,
            },
        }
        for doc in docs
    ]
    success, _ = bulk(client, actions)
    return success
