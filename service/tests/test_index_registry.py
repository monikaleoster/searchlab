import pytest

from searchlab.opensearch import index_registry


@pytest.fixture(autouse=True)
def _redirect_registry_path(tmp_path, monkeypatch):
    monkeypatch.setattr(index_registry, "_REGISTRY_PATH", tmp_path / "data" / "index_registry.json")
    return tmp_path


def _entry(key="my-index", index=None):
    return {
        "index": index or f"searchlab-{key}",
        "key": key,
        "label": key,
        "createdAt": "2026-07-14T00:00:00+00:00",
        "schemaSource": "uploaded",
    }


def test_load_registry_missing_file_returns_empty_list():
    assert index_registry.load_registry() == []


def test_save_entry_creates_parent_directory_and_round_trips():
    index_registry.save_entry(_entry())

    assert index_registry.load_registry() == [_entry()]


def test_save_entry_appends_to_existing_entries():
    index_registry.save_entry(_entry("first"))
    index_registry.save_entry(_entry("second"))

    entries = index_registry.load_registry()
    assert [e["key"] for e in entries] == ["first", "second"]


def test_find_by_key_found_and_not_found():
    index_registry.save_entry(_entry("my-index"))

    assert index_registry.find_by_key("my-index") == _entry("my-index")
    assert index_registry.find_by_key("does-not-exist") is None


def test_find_by_index_found_and_not_found():
    index_registry.save_entry(_entry("my-index"))

    assert index_registry.find_by_index("searchlab-my-index") == _entry("my-index")
    assert index_registry.find_by_index("searchlab-does-not-exist") is None


def test_key_exists():
    index_registry.save_entry(_entry("my-index"))

    assert index_registry.key_exists("my-index") is True
    assert index_registry.key_exists("other") is False
