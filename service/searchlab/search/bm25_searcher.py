from dataclasses import dataclass

from opensearchpy import OpenSearch


@dataclass
class SearchHit:
    rank: int
    score: float
    doc_id: str
    source_filename: str
    page_number: int
    snippet: str


def search(client: OpenSearch, question: str, top_k: int, index: str) -> list[SearchHit]:
    resp = client.search(
        index=index,
        body={"query": {"match": {"chunk_text": question}}, "size": top_k},
    )
    hits = []
    for rank, hit in enumerate(resp["hits"]["hits"], start=1):
        src = hit.get("_source", {})
        text = src.get("chunk_text", "")
        hits.append(
            SearchHit(
                rank=rank,
                score=hit.get("_score", 0.0),
                doc_id=hit["_id"],
                source_filename=src.get("source_filename", ""),
                page_number=src.get("page_number", 0),
                snippet=text[:200],
            )
        )
    return hits
