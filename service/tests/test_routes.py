import asyncio

import pytest

from searchlab.opensearch import index_registry
from searchlab.web import routes


@pytest.fixture(autouse=True)
def _redirect_registry_path(tmp_path, monkeypatch):
    monkeypatch.setattr(index_registry, "_REGISTRY_PATH", tmp_path / "data" / "index_registry.json")
    return tmp_path


def test_resolve_index_default_falls_back_to_config_index_name(monkeypatch):
    monkeypatch.setattr(routes.config, "index_name", lambda: "searchlab-v0")

    assert routes._resolve_index("default") == "searchlab-v0"


def test_resolve_index_default_prefers_explicit_default_index():
    assert routes._resolve_index("default", default_index="searchlab-custom") == "searchlab-custom"


def test_resolve_index_hardcoded_dataset_index_wins_over_registry():
    index_registry.save_entry({
        "index": "searchlab-shadow", "key": "nfcorpus", "label": "shadow",
        "createdAt": "2026-07-14T00:00:00+00:00", "schemaSource": "uploaded",
    })

    assert routes._resolve_index("nfcorpus") == "searchlab-nfcorpus"


def test_resolve_index_resolves_registry_key():
    index_registry.save_entry({
        "index": "searchlab-my-index", "key": "my-index", "label": "My Index",
        "createdAt": "2026-07-14T00:00:00+00:00", "schemaSource": "uploaded",
    })

    assert routes._resolve_index("my-index") == "searchlab-my-index"


def test_resolve_index_unknown_dataset_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(routes.config, "index_name", lambda: "searchlab-v0")

    assert routes._resolve_index("does-not-exist") == "searchlab-v0"


# ── _build_eval_command index override (Group 9) ────────────────────

def test_build_eval_command_ingest_appends_index_when_given():
    cmd = routes._build_eval_command("ingest", "nfcorpus", index="searchlab-custom")

    assert cmd == ["uv", "run", "searchlab-eval", "ingest", "--dataset", "nfcorpus", "--index", "searchlab-custom"]


def test_build_eval_command_query_appends_index_when_given():
    cmd = routes._build_eval_command("query", "nfcorpus", index="searchlab-custom")

    assert cmd == ["uv", "run", "searchlab-eval", "query", "--dataset", "nfcorpus", "--index", "searchlab-custom"]


def test_build_eval_command_ingest_omits_index_when_blank():
    cmd = routes._build_eval_command("ingest", "nfcorpus")

    assert "--index" not in cmd


def test_build_eval_command_download_unaffected_by_index():
    cmd = routes._build_eval_command("download", "nfcorpus", index="searchlab-custom")

    assert "--index" not in cmd


def test_build_eval_command_ragas_unaffected_by_index():
    cmd = routes._build_eval_command("ragas", "nfcorpus", index="searchlab-custom")

    assert "--index" not in cmd


def test_build_eval_command_metrics_unaffected_by_index():
    cmd = routes._build_eval_command("metrics", "nfcorpus", run_id="run1", index="searchlab-custom")

    assert "--index" not in cmd


# ── /api/query index override (Group 9) ─────────────────────────────

def test_api_query_explicit_index_bypasses_resolve_index(monkeypatch):
    captured = {}

    def fake_bm25_search(client, query, top_k, index):
        captured["index"] = index
        return []

    monkeypatch.setattr(routes, "create_client", lambda: object())
    monkeypatch.setattr(routes, "bm25_search", fake_bm25_search)
    monkeypatch.setattr(routes, "_resolve_index", lambda dataset: (_ for _ in ()).throw(
        AssertionError("_resolve_index should not be called when index is explicit")))

    result = asyncio.run(routes.api_query(query="test", topK=5, dataset="nfcorpus", index="searchlab-custom"))

    assert captured["index"] == "searchlab-custom"
    assert result["index"] == "searchlab-custom"


def test_api_query_empty_index_preserves_dataset_resolution(monkeypatch):
    captured = {}

    def fake_bm25_search(client, query, top_k, index):
        captured["index"] = index
        return []

    monkeypatch.setattr(routes, "create_client", lambda: object())
    monkeypatch.setattr(routes, "bm25_search", fake_bm25_search)
    monkeypatch.setattr(routes, "_resolve_index", lambda dataset: f"searchlab-{dataset}")

    result = asyncio.run(routes.api_query(query="test", topK=5, dataset="nfcorpus", index=""))

    assert captured["index"] == "searchlab-nfcorpus"
    assert result["index"] == "searchlab-nfcorpus"
