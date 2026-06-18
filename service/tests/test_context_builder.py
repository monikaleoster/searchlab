from searchlab.rag.context_builder import build
from searchlab.search.bm25_searcher import SearchHit


def _hit(rank, filename, snippet="text"):
    return SearchHit(rank=rank, score=1.0, doc_id=f"id-{rank}",
                     source_filename=filename, page_number=0, snippet=snippet)


def test_empty_list():
    assert build([]) == ""


def test_single_hit():
    result = build([_hit(1, "doc.pdf", "some passage")])
    assert result == "[1] doc.pdf: some passage"


def test_multiple_hits_sequential():
    hits = [_hit(1, "a.pdf", "first"), _hit(2, "b.pdf", "second")]
    lines = build(hits).splitlines()
    assert lines[0] == "[1] a.pdf: first"
    assert lines[1] == "[2] b.pdf: second"


def test_ranking_matches_hit_rank():
    hits = [_hit(3, "c.pdf", "third"), _hit(7, "d.pdf", "seventh")]
    result = build(hits)
    assert "[3]" in result
    assert "[7]" in result
