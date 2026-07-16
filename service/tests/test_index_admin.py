import pytest
from opensearchpy.exceptions import RequestError

from searchlab.opensearch import index_admin, index_registry


@pytest.fixture(autouse=True)
def _redirect_registry_path(tmp_path, monkeypatch):
    monkeypatch.setattr(index_registry, "_REGISTRY_PATH", tmp_path / "data" / "index_registry.json")
    return tmp_path


class _FakeIndicesClient:
    def __init__(self, existing=None, reject=False):
        self._existing = set(existing or [])
        self._reject = reject
        self.created = []

    def exists(self, index):
        return index in self._existing

    def create(self, index, body):
        if self._reject:
            raise RequestError(400, "mapper_parsing_exception", "no such type")
        self.created.append((index, body))
        self._existing.add(index)


class _FakeCatClient:
    def __init__(self, rows):
        self._rows = rows

    def indices(self, index, format, h):
        return self._rows


class _FakeClient:
    def __init__(self, existing=None, reject=False, cat_rows=None):
        self.indices = _FakeIndicesClient(existing, reject)
        self.cat = _FakeCatClient(cat_rows or [])


# ── validate_key ─────────────────────────────────────────────────────

def test_validate_key_rejects_empty():
    with pytest.raises(ValueError):
        index_admin.validate_key("")


def test_validate_key_rejects_bad_characters():
    with pytest.raises(ValueError):
        index_admin.validate_key("My Index!")


def test_validate_key_rejects_reserved_names():
    for key in ("default", "nfcorpus", "fiqa"):
        with pytest.raises(ValueError, match="reserved"):
            index_admin.validate_key(key)


def test_validate_key_accepts_valid_key():
    index_admin.validate_key("my-index-1")  # no raise


# ── create_index ─────────────────────────────────────────────────────

def test_create_index_success_returns_full_name():
    client = _FakeClient()

    full_name = index_admin.create_index(client, "my-index", {"mappings": {}})

    assert full_name == "searchlab-my-index"
    assert client.indices.created == [("searchlab-my-index", {"mappings": {}})]


def test_create_index_does_not_write_registry_itself():
    client = _FakeClient()

    index_admin.create_index(client, "my-index", {"mappings": {}})

    assert index_registry.load_registry() == []


def test_create_index_rejects_invalid_key_before_any_opensearch_call():
    client = _FakeClient()

    with pytest.raises(ValueError):
        index_admin.create_index(client, "Bad Key", {"mappings": {}})

    assert client.indices.created == []


def test_create_index_rejects_duplicate_opensearch_index():
    client = _FakeClient(existing={"searchlab-my-index"})

    with pytest.raises(ValueError, match="already exists"):
        index_admin.create_index(client, "my-index", {"mappings": {}})


def test_create_index_rejects_duplicate_registry_key():
    client = _FakeClient()
    index_registry.save_entry({
        "index": "searchlab-my-index", "key": "my-index", "label": "my-index",
        "createdAt": "2026-07-14T00:00:00+00:00", "schemaSource": "uploaded",
    })

    with pytest.raises(ValueError, match="already exists"):
        index_admin.create_index(client, "my-index", {"mappings": {}})


def test_create_index_propagates_opensearch_rejection():
    client = _FakeClient(reject=True)

    with pytest.raises(RequestError):
        index_admin.create_index(client, "my-index", {"mappings": {"bad": "shape"}})

    assert client.indices.created == []


# ── list_indexes ─────────────────────────────────────────────────────

def test_list_indexes_merges_registry_metadata():
    client = _FakeClient(cat_rows=[
        {"index": "searchlab-my-index", "docs.count": "5"},
    ])
    index_registry.save_entry({
        "index": "searchlab-my-index", "key": "my-index", "label": "My Index",
        "createdAt": "2026-07-14T00:00:00+00:00", "schemaSource": "uploaded",
    })

    result = index_admin.list_indexes(client)

    assert result == [{
        "index": "searchlab-my-index",
        "label": "My Index",
        "docCount": 5,
        "schemaSource": "uploaded",
        "createdAt": "2026-07-14T00:00:00+00:00",
    }]


def test_list_indexes_handles_index_with_no_registry_entry():
    client = _FakeClient(cat_rows=[
        {"index": "searchlab-v0", "docs.count": "12"},
    ])

    result = index_admin.list_indexes(client)

    assert result == [{
        "index": "searchlab-v0",
        "label": "searchlab-v0",
        "docCount": 12,
        "schemaSource": "pre-existing",
        "createdAt": None,
    }]


def test_list_indexes_sorted_by_index_name():
    client = _FakeClient(cat_rows=[
        {"index": "searchlab-v0", "docs.count": "1"},
        {"index": "searchlab-fiqa", "docs.count": "2"},
    ])

    result = index_admin.list_indexes(client)

    assert [e["index"] for e in result] == ["searchlab-fiqa", "searchlab-v0"]
