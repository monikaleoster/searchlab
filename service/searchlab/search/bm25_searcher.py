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


def _chunk_text_match(text: str) -> dict:
    """The one place `chunk_text` matching is defined, so search() and
    highlight_document() can't quietly drift into scoring documents differently."""
    return {"match": {"chunk_text": text}}


def search(client: OpenSearch, question: str, top_k: int, index: str) -> list[SearchHit]:
    resp = client.search(
        index=index,
        body={"query": _chunk_text_match(question), "size": top_k},
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


def highlight_document(client: OpenSearch, query: str, doc_id: str, index: str) -> list[str]:
    """Live OpenSearch highlight for one known doc_id against a query.

    The `filter`/`term` on `_id` returns the doc (non-scoring) if it exists in the
    index at all; `should` + `minimum_should_match: 0` means the match clause only
    contributes scoring/highlighting, never excludes the hit. That's what lets the
    caller tell "doc not in the live index" (zero hits) apart from "doc exists but
    nothing matched" (one hit, no highlight fragments).
    """
    resp = client.search(
        index=index,
        body={
            "query": {
                "bool": {
                    "filter": [{"term": {"_id": doc_id}}],
                    "should": [_chunk_text_match(query)],
                    "minimum_should_match": 0,
                }
            },
            "highlight": {"fields": {"chunk_text": {}}},
            "size": 1,
        },
    )
    hits = resp["hits"]["hits"]
    if not hits:
        raise FileNotFoundError(f"Document '{doc_id}' not found in live index '{index}'")
    return hits[0].get("highlight", {}).get("chunk_text", [])
