"""Unit tests for semantic_search: manifest, application derivation, build_records, search (mocked)."""

from unittest.mock import MagicMock

import pytest

from semantic_search import (
    application_from_path,
    build_records_from_project,
    load_manifest,
    namespace_for_project,
    search_knowledge_base,
    _metadata_for_pinecone,
)


class TestApplicationFromPath:
    """Application name derived from first path segment or 'default' at root."""

    def test_file_at_root_returns_default(self):
        assert application_from_path("readme.md") == "default"
        assert application_from_path("file.txt") == "default"

    def test_file_in_subfolder_returns_first_segment(self):
        assert application_from_path("MyApp/doc.pdf") == "MyApp"
        assert application_from_path("FinanceApp/reports/Q1.xlsx") == "FinanceApp"

    def test_backslash_normalized(self):
        assert application_from_path("MyApp\\doc.pdf") == "MyApp"

    def test_empty_or_slash_returns_default(self):
        assert application_from_path("") == "default"
        assert application_from_path("/") == "default"


class TestLoadManifest:
    """manifest.json loading from project directory."""

    def test_missing_manifest_returns_empty_dict(self, tmp_path):
        assert load_manifest(str(tmp_path)) == {}

    def test_invalid_json_returns_empty_dict(self, tmp_path):
        (tmp_path / "manifest.json").write_text("not json {", encoding="utf-8")
        assert load_manifest(str(tmp_path)) == {}

    def test_valid_manifest_returns_dict(self, temp_project_with_manifest):
        data = load_manifest(str(temp_project_with_manifest))
        assert isinstance(data, dict)
        assert "MyApp" in data
        assert data["MyApp"].get("technology") == "Python"
        assert "default" in data


class TestMetadataForPinecone:
    """Manifest values converted to Pinecone-safe types."""

    def test_string_number_bool_preserved(self):
        out = _metadata_for_pinecone({"a": "x", "b": 1, "c": True})
        assert out["a"] == "x"
        assert out["b"] == 1
        assert out["c"] is True

    def test_list_becomes_list_of_strings(self):
        out = _metadata_for_pinecone({"tags": ["a", "b"]})
        assert out["tags"] == ["a", "b"]

    def test_none_skipped(self):
        out = _metadata_for_pinecone({"a": "x", "b": None})
        assert "a" in out
        assert "b" not in out


class TestBuildRecordsFromProject:
    """build_records_from_project produces records with content and metadata."""

    def test_records_have_required_fields(self, temp_project_dir):
        records = build_records_from_project(str(temp_project_dir))
        assert len(records) >= 1
        for r in records:
            assert "_id" in r
            assert "content" in r
            assert "file_path" in r
            assert "category" in r
            assert "application" in r
            assert "content_type" in r

    def test_manifest_metadata_applied_to_records(self, temp_project_with_manifest):
        records = build_records_from_project(str(temp_project_with_manifest))
        app_records = [r for r in records if r.get("application") == "MyApp"]
        assert len(app_records) >= 1
        assert app_records[0].get("technology") == "Python"
        assert app_records[0].get("tools") == "Docker"

    def test_manifest_file_not_indexed(self, temp_project_with_manifest):
        records = build_records_from_project(str(temp_project_with_manifest))
        paths = [r["file_path"] for r in records]
        assert not any("manifest.json" in p for p in paths)

    def test_root_file_has_application_default(self, temp_project_dir):
        records = build_records_from_project(str(temp_project_dir))
        root_records = [r for r in records if r.get("file_path") == "readme.txt"]
        assert len(root_records) >= 1
        assert root_records[0]["application"] == "default"


class TestNamespaceForProject:
    """Namespace is stable and derived from absolute path."""

    def test_same_path_same_namespace(self):
        ns1 = namespace_for_project("/some/path")
        ns2 = namespace_for_project("/some/path")
        assert ns1 == ns2
        assert ns1.startswith("project_")

    def test_different_path_different_namespace(self):
        ns1 = namespace_for_project("/path/a")
        ns2 = namespace_for_project("/path/b")
        assert ns1 != ns2


class TestSearchKnowledgeBase:
    """search_knowledge_base builds correct query and calls index (mocked)."""

    def test_search_calls_index_with_query_and_filters(self):
        mock_index = MagicMock()
        mock_response = MagicMock()
        mock_response.result.hits = []
        mock_index.search.return_value = mock_response

        search_knowledge_base(
            mock_index,
            namespace="test_ns",
            query="test query",
            category_filter="pdf",
            application_filter="MyApp",
            top_k=5,
        )

        mock_index.search.assert_called_once()
        call_kw = mock_index.search.call_args[1]
        assert call_kw["namespace"] == "test_ns"
        query_dict = call_kw["query"]
        assert "inputs" in query_dict
        assert query_dict["inputs"].get("text") == "test query"
        assert "filter" in query_dict
        assert query_dict["filter"] is not None

    def test_search_no_filters(self):
        mock_index = MagicMock()
        mock_response = MagicMock()
        mock_response.result.hits = []
        mock_index.search.return_value = mock_response

        search_knowledge_base(mock_index, namespace="ns", query="q", top_k=3)

        mock_index.search.assert_called_once()
        call_kw = mock_index.search.call_args[1]
        assert call_kw["namespace"] == "ns"
        assert call_kw["query"]["inputs"]["text"] == "q"
