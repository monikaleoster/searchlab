import pytest

from searchlab.search.bm25_searcher import highlight_document


class _FakeClient:
    """Stands in for OpenSearch's client — just enough of `.search()` to drive
    highlight_document() without a live cluster."""

    def __init__(self, response):
        self._response = response
        self.last_call = None

    def search(self, index, body):
        self.last_call = {"index": index, "body": body}
        return self._response


def _hits(hit_list):
    return {"hits": {"hits": hit_list}}


def test_highlight_document_returns_fragments_when_matched():
    client = _FakeClient(_hits([
        {
            "_id": "MED-14",
            "_source": {"chunk_text": "cholesterol statin drugs"},
            "highlight": {"chunk_text": ["<em>cholesterol</em> statin drugs"]},
        }
    ]))

    fragments = highlight_document(client, "cholesterol", "MED-14", "searchlab-nfcorpus")

    assert fragments == ["<em>cholesterol</em> statin drugs"]
    assert client.last_call["body"]["query"]["bool"]["filter"] == [{"term": {"_id": "MED-14"}}]
    assert client.last_call["body"]["query"]["bool"]["should"] == [{"match": {"chunk_text": "cholesterol"}}]
    assert client.last_call["body"]["query"]["bool"]["minimum_should_match"] == 0


def test_highlight_document_returns_empty_list_when_no_term_overlap():
    # Doc exists (one hit), but nothing matched the query — no `highlight` block at all.
    client = _FakeClient(_hits([
        {"_id": "MED-14", "_source": {"chunk_text": "cholesterol statin drugs"}}
    ]))

    fragments = highlight_document(client, "unrelated query terms", "MED-14", "searchlab-nfcorpus")

    assert fragments == []


def test_highlight_document_raises_file_not_found_when_doc_missing_from_index():
    client = _FakeClient(_hits([]))

    with pytest.raises(FileNotFoundError, match="MED-999"):
        highlight_document(client, "cholesterol", "MED-999", "searchlab-nfcorpus")
