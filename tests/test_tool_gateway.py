"""Unit tests for the Tool Gateway registry and the Tavily direct tool (no network)."""

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from backend.services.tool_gateway import registry
from backend.services.tool_gateway.direct_tools import tavily_search as tavily


@pytest.fixture
def isolated_registry(monkeypatch):
    """Give each test an empty registry and a fresh singleton."""
    monkeypatch.setattr(registry, "_registry", {})
    monkeypatch.setattr(registry, "_gateway_instance", None)
    return registry


class TestToolGatewayRegistry:
    def test_register_invoke_and_describe(self, isolated_registry):
        gw = isolated_registry.ToolGateway()
        gw.register_tool("echo", {"name": "echo", "description": "Echo"}, lambda **kw: kw)

        assert gw.invoke("echo", {"a": 1}) == {"a": 1}
        assert gw.list_tools() == ["echo"]
        assert gw.get_descriptor("echo")["description"] == "Echo"
        assert gw.get_descriptor("missing") is None

    def test_invoke_unknown_tool_raises_key_error(self, isolated_registry):
        with pytest.raises(KeyError, match="Tool not registered"):
            isolated_registry.ToolGateway().invoke("nope", {})

    def test_reregister_last_wins(self, isolated_registry):
        gw = isolated_registry.ToolGateway()
        gw.register_tool("t", {"name": "t"}, lambda **kw: "old")
        gw.register_tool("t", {"name": "t"}, lambda **kw: "new")
        assert gw.invoke("t", {}) == "new"

    def test_get_gateway_is_singleton_with_web_search(self, isolated_registry):
        gw = isolated_registry.get_gateway()
        assert gw is isolated_registry.get_gateway()
        assert tavily.TOOL_NAME in gw.list_tools()


def _fake_urlopen_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


class TestTavilySearch:
    @pytest.fixture(autouse=True)
    def _no_diagnostics(self):
        with patch("backend.services.diagnostics.recorder.record_tool_call"):
            yield

    def test_missing_api_key_returns_empty_without_network(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        with patch.object(tavily.urllib.request, "urlopen") as urlopen:
            assert tavily.tavily_search("azure sql") == []
        urlopen.assert_not_called()

    def test_success_parses_and_normalises_results(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        payload = {"results": [
            {"title": " Azure SQL ", "url": "https://learn.microsoft.com/x ", "content": " snippet "},
            "not-a-dict",
            {"title": None, "url": "https://docs.aws.amazon.com/y"},
        ]}
        with patch.object(tavily.urllib.request, "urlopen", return_value=_fake_urlopen_response(payload)) as urlopen:
            results = tavily.tavily_search(
                "oracle to azure", max_results=99, search_depth="bogus",
                include_domains=["learn.microsoft.com"], unexpected_param="ignored",
            )

        assert results == [
            {"title": "Azure SQL", "url": "https://learn.microsoft.com/x", "content": "snippet"},
            {"title": "", "url": "https://docs.aws.amazon.com/y", "content": ""},
        ]
        request = urlopen.call_args.args[0]
        assert request.full_url == tavily.TAVILY_SEARCH_URL
        assert request.get_header("Authorization") == "Bearer tvly-test"
        body = json.loads(request.data)
        assert body["max_results"] == 20          # clamped to API max
        assert body["search_depth"] == "basic"    # invalid depth falls back
        assert body["include_domains"] == ["learn.microsoft.com"]
        assert "unexpected_param" not in body

    def test_http_error_raises_tavily_error_with_detail(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        err = urllib.error.HTTPError(
            tavily.TAVILY_SEARCH_URL, 429, "Too Many Requests", {},
            io.BytesIO(json.dumps({"detail": "quota exceeded"}).encode()),
        )
        with patch.object(tavily.urllib.request, "urlopen", side_effect=err):
            with pytest.raises(tavily.TavilySearchError, match=r"429.*quota exceeded"):
                tavily.tavily_search("q")

    def test_network_error_raises_tavily_error(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        with patch.object(tavily.urllib.request, "urlopen", side_effect=urllib.error.URLError("dns")):
            with pytest.raises(tavily.TavilySearchError, match="network or parse"):
                tavily.tavily_search("q")
