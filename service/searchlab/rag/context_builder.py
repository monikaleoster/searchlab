from ..search.bm25_searcher import SearchHit


def build(hits: list[SearchHit]) -> str:
    if not hits:
        return ""
    return "\n".join(f"[{h.rank}] {h.source_filename}: {h.snippet}" for h in hits)
