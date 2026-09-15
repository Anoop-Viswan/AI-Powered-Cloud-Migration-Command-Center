"""API tests for /api/health, /api/search and /api/chat (Pinecone and LLM mocked, real FastAPI stack)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


class _Hit(dict):
    """Pinecone search hit: subscriptable for _id/_score, with a .fields mapping."""

    def __init__(self, _id, score, fields):
        super().__init__(_id=_id, _score=score)
        self.fields = fields


def _search_response(hits):
    return SimpleNamespace(result=SimpleNamespace(hits=hits))


HITS = [
    _Hit("doc-1", 0.91, {"content": "Oracle to Azure SQL", "file_path": "kb/db.md", "category": "md", "application": "FinanceHub"}),
    _Hit("doc-2", 0.74, {"content": "Use AKS for Spring Boot"}),
]


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def kb(monkeypatch):
    """Configured project dir + fake Pinecone client; returns the search mock."""
    monkeypatch.setenv("PINECONE_PROJECT_DIR", "/tmp/coe-test-project")
    pc = MagicMock()
    with patch("backend.semantic_search.get_client", return_value=pc), \
         patch("backend.semantic_search.search_knowledge_base", return_value=_search_response(HITS)) as search:
        yield search


def test_health(client, monkeypatch):
    monkeypatch.delenv("PINECONE_PROJECT_DIR", raising=False)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "project_dir_configured": False}


class TestSearchApi:
    def test_search_returns_mapped_hits(self, client, kb):
        r = client.post("/api/search", json={"query": "oracle", "category": "md", "top_k": 3})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["query"] == "oracle"
        assert data["hits"][0] == {
            "id": "doc-1", "score": 0.91, "content": "Oracle to Azure SQL",
            "file_path": "kb/db.md", "category": "md", "application": "FinanceHub",
        }
        # Missing metadata fields default to empty strings
        assert data["hits"][1]["file_path"] == "" and data["hits"][1]["application"] == ""
        _, kwargs = kb.call_args
        assert kwargs == {"category_filter": "md", "application_filter": None, "top_k": 3}

    def test_search_without_project_dir_is_503(self, client, monkeypatch):
        monkeypatch.delenv("PINECONE_PROJECT_DIR", raising=False)
        r = client.post("/api/search", json={"query": "oracle"})
        assert r.status_code == 503

    def test_search_validates_body(self, client):
        assert client.post("/api/search", json={}).status_code == 422


class TestChatApi:
    def test_chat_passes_kb_context_and_overrides_to_llm(self, client, kb):
        with patch("backend.routers.chat.summarize_with_llm", return_value="Use Azure SQL MI.") as summarize:
            r = client.post("/api/chat", json={
                "query": "How to migrate Oracle?", "application": "FinanceHub",
                "temperature": 0.1, "max_tokens": 200,
            })
        assert r.status_code == 200, r.text
        assert r.json() == {"query": "How to migrate Oracle?", "answer": "Use Azure SQL MI.", "sources_used": 2}
        args, kwargs = summarize.call_args
        assert args == ("How to migrate Oracle?", ["Oracle to Azure SQL", "Use AKS for Spring Boot"])
        assert kwargs == {"system_prompt": None, "temperature": 0.1, "max_tokens": 200}

    def test_chat_without_project_dir_is_503(self, client, monkeypatch):
        monkeypatch.delenv("PINECONE_PROJECT_DIR", raising=False)
        assert client.post("/api/chat", json={"query": "q"}).status_code == 503
