"""Contract tests for the LLM provider layer against a local stub HTTP server.

Unlike the agent tests (which replace the LLM with MagicMock), these run the REAL
langchain-openai / langchain-anthropic / openai / anthropic SDK code end to end:
request building, HTTP call, response parsing. Only the remote API is faked.

Why: dependency bumps in the LLM stack (e.g. openai 2.x -> 3.x, langchain-core
minors) break at exactly this seam, and mocked tests cannot see it. No network,
no API keys, no extra test dependencies (stdlib http.server).
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from backend.services import llm as llm_service
from backend.services.diagnostics import recorder
from backend.services.llm_provider import get_llm

STUB_REPLY = "Stubbed migration answer."


def _openai_chat_completion(model: str) -> dict:
    return {
        "id": "chatcmpl-stub",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": STUB_REPLY},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
    }


def _anthropic_message(model: str) -> dict:
    return {
        "id": "msg_stub",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": STUB_REPLY}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 13, "output_tokens": 5},
    }


class _StubHandler(BaseHTTPRequestHandler):
    """Records each request and answers in the provider's wire format by path."""

    requests: list[dict] = []

    def log_message(self, *args):  # keep pytest output clean
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        path = self.path.split("?")[0]
        self.requests.append({
            "path": self.path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": body,
        })

        if body.get("model") == "force-error":
            self._send_json(400, {"error": {"message": "stub: forced bad request", "type": "invalid_request_error"}})
            return
        if path.endswith("/chat/completions"):
            payload = _openai_chat_completion(body.get("model", "azure-deployment"))
        elif path.endswith("/v1/messages"):
            payload = _anthropic_message(body.get("model", ""))
        else:
            # Unknown endpoint = the SDK changed which API it calls. Fail loudly.
            self._send_json(404, {"error": {"message": f"stub: unexpected path {path}"}})
            return
        self._send_json(200, payload)

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def stub_server():
    _StubHandler.requests = []
    server = HTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", _StubHandler.requests
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def clean_llm_env(monkeypatch):
    """Isolate from the developer's .env / shell so tests are deterministic."""
    for var in (
        "LLM_PROVIDER", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TEMPERATURE", "OPENAI_MAX_TOKENS",
        "OPENAI_API_BASE", "OPENAI_BASE_URL", "OPENAI_SYSTEM_PROMPT", "OPENAI_API_VERSION",
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_API_URL", "ANTHROPIC_BASE_URL",
        "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT",
        "LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING",
    ):
        monkeypatch.delenv(var, raising=False)
    # Never let a test run ship traces to LangSmith
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    return monkeypatch


@pytest.fixture
def recorded_calls():
    """Capture diagnostics records instead of writing to SQLite."""
    calls: list[dict] = []
    with patch.object(recorder, "record_llm_call", side_effect=lambda **kw: calls.append(kw)):
        yield calls


def _messages():
    return [SystemMessage(content="You are a test."), HumanMessage(content="Plan a migration.")]


# --- Provider factory: correct class and settings for each provider -----------------

class TestGetLlmFactory:
    def test_default_provider_is_openai(self, clean_llm_env):
        clean_llm_env.setenv("OPENAI_API_KEY", "sk-test")
        from langchain_openai import ChatOpenAI

        llm = get_llm()
        assert isinstance(llm, ChatOpenAI)
        assert isinstance(llm, BaseChatModel)
        assert llm.model_name == "gpt-4o-mini"
        assert llm.temperature == 0.3
        assert llm.max_tokens == 4096

    def test_overrides_beat_env_defaults(self, clean_llm_env):
        clean_llm_env.setenv("OPENAI_API_KEY", "sk-test")
        clean_llm_env.setenv("OPENAI_MODEL", "gpt-env-model")
        clean_llm_env.setenv("OPENAI_TEMPERATURE", "0.9")
        clean_llm_env.setenv("OPENAI_MAX_TOKENS", "999")

        from_env = get_llm()
        assert (from_env.model_name, from_env.temperature, from_env.max_tokens) == ("gpt-env-model", 0.9, 999)

        explicit = get_llm(model="gpt-explicit", temperature=0.0, max_tokens=10)
        assert (explicit.model_name, explicit.temperature, explicit.max_tokens) == ("gpt-explicit", 0.0, 10)

    def test_invalid_numeric_env_falls_back_to_defaults(self, clean_llm_env):
        clean_llm_env.setenv("OPENAI_API_KEY", "sk-test")
        clean_llm_env.setenv("OPENAI_TEMPERATURE", "hot")
        clean_llm_env.setenv("OPENAI_MAX_TOKENS", "lots")
        llm = get_llm()
        assert (llm.temperature, llm.max_tokens) == (0.3, 4096)

    def test_anthropic_provider(self, clean_llm_env):
        clean_llm_env.setenv("LLM_PROVIDER", "Anthropic ")  # case/whitespace tolerant
        clean_llm_env.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from langchain_anthropic import ChatAnthropic

        llm = get_llm(max_tokens=123)
        assert isinstance(llm, ChatAnthropic)
        assert llm.model == "claude-3-5-sonnet-20241022"
        assert llm.max_tokens == 123

    def test_azure_provider(self, clean_llm_env):
        clean_llm_env.setenv("LLM_PROVIDER", "azure_openai")
        clean_llm_env.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
        clean_llm_env.setenv("AZURE_OPENAI_API_KEY", "azure-test")
        clean_llm_env.setenv("AZURE_OPENAI_DEPLOYMENT", "my-deployment")
        clean_llm_env.setenv("OPENAI_API_VERSION", "2024-10-21")
        from langchain_openai import AzureChatOpenAI

        llm = get_llm()
        assert isinstance(llm, AzureChatOpenAI)
        assert llm.deployment_name == "my-deployment"

    def test_unknown_provider_raises(self, clean_llm_env):
        clean_llm_env.setenv("LLM_PROVIDER", "bard")
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            get_llm()


# --- Wire contract: real SDK request/response round trip ----------------------------

class TestProviderWireContract:
    def test_openai_round_trip(self, stub_server, clean_llm_env, recorded_calls):
        base_url, requests = stub_server
        clean_llm_env.setenv("OPENAI_API_KEY", "sk-test")
        clean_llm_env.setenv("OPENAI_BASE_URL", f"{base_url}/v1")
        clean_llm_env.setenv("OPENAI_API_BASE", f"{base_url}/v1")

        llm = get_llm(temperature=0.1, max_tokens=50)
        response = recorder.invoke_llm(llm, _messages(), "research", assessment_id="a-1")

        assert response.content == STUB_REPLY
        assert len(requests) == 1
        req = requests[0]
        assert req["path"].endswith("/v1/chat/completions")
        assert req["headers"].get("authorization") == "Bearer sk-test"
        body = req["body"]
        assert body["model"] == "gpt-4o-mini"
        assert body["temperature"] == 0.1
        assert body.get("max_completion_tokens", body.get("max_tokens")) == 50
        assert [m["role"] for m in body["messages"]] == ["system", "user"]
        assert body["messages"][1]["content"] == "Plan a migration."
        assert body.get("stream") in (None, False)

        # Diagnostics must still capture model + token usage from the parsed response
        assert len(recorded_calls) == 1
        rec = recorded_calls[0]
        assert rec["status"] == "ok"
        assert rec["operation"] == "research"
        assert rec["model"] == "gpt-4o-mini"
        assert rec["assessment_id"] == "a-1"
        assert (rec["input_tokens"], rec["output_tokens"]) == (11, 7)

    def test_anthropic_round_trip(self, stub_server, clean_llm_env, recorded_calls):
        base_url, requests = stub_server
        clean_llm_env.setenv("LLM_PROVIDER", "anthropic")
        clean_llm_env.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        clean_llm_env.setenv("ANTHROPIC_API_URL", base_url)
        clean_llm_env.setenv("ANTHROPIC_BASE_URL", base_url)

        llm = get_llm(max_tokens=64)
        response = recorder.invoke_llm(llm, _messages(), "summarize")

        assert response.content == STUB_REPLY
        assert len(requests) == 1
        req = requests[0]
        assert req["path"].endswith("/v1/messages")
        assert req["headers"].get("x-api-key") == "sk-ant-test"
        body = req["body"]
        assert body["model"] == "claude-3-5-sonnet-20241022"
        assert body["max_tokens"] == 64
        # Anthropic takes the system prompt as a top-level field, not a message
        assert "You are a test." in json.dumps(body.get("system"))
        assert [m["role"] for m in body["messages"]] == ["user"]

        rec = recorded_calls[0]
        assert rec["status"] == "ok"
        assert (rec["input_tokens"], rec["output_tokens"]) == (13, 5)

    def test_azure_round_trip(self, stub_server, clean_llm_env, recorded_calls):
        base_url, requests = stub_server
        clean_llm_env.setenv("LLM_PROVIDER", "azure_openai")
        clean_llm_env.setenv("AZURE_OPENAI_ENDPOINT", base_url)
        clean_llm_env.setenv("AZURE_OPENAI_API_KEY", "azure-test")
        clean_llm_env.setenv("AZURE_OPENAI_DEPLOYMENT", "coe-gpt")
        clean_llm_env.setenv("OPENAI_API_VERSION", "2024-10-21")

        response = recorder.invoke_llm(get_llm(), _messages(), "chat")

        assert response.content == STUB_REPLY
        req = requests[0]
        assert "/openai/deployments/coe-gpt/chat/completions" in req["path"]
        assert "api-version=2024-10-21" in req["path"]
        assert req["headers"].get("api-key") == "azure-test"
        assert recorded_calls[0]["status"] == "ok"

    def test_api_error_is_recorded_and_raised(self, stub_server, clean_llm_env, recorded_calls):
        base_url, _ = stub_server
        clean_llm_env.setenv("OPENAI_API_KEY", "sk-test")
        clean_llm_env.setenv("OPENAI_BASE_URL", f"{base_url}/v1")
        clean_llm_env.setenv("OPENAI_API_BASE", f"{base_url}/v1")

        llm = get_llm(model="force-error")  # stub answers 400 for this model
        llm.max_retries = 0  # fail fast instead of SDK backoff retries
        with pytest.raises(Exception):
            recorder.invoke_llm(llm, _messages(), "chat")
        assert recorded_calls[0]["status"] == "error"
        assert recorded_calls[0]["error_message"]


# --- Chat service: user-facing behaviour on top of the provider ---------------------

class TestSummarizeWithLlm:
    def test_not_configured_returns_guidance(self, clean_llm_env):
        answer = llm_service.summarize_with_llm("q", ["ctx"])
        assert answer.startswith("LLM is not configured")

    def test_end_to_end_with_real_sdk(self, stub_server, clean_llm_env, recorded_calls):
        base_url, requests = stub_server
        clean_llm_env.setenv("OPENAI_API_KEY", "sk-test")
        clean_llm_env.setenv("OPENAI_BASE_URL", f"{base_url}/v1")
        clean_llm_env.setenv("OPENAI_API_BASE", f"{base_url}/v1")

        chunks = [f"chunk-{i}" for i in range(15)]
        answer = llm_service.summarize_with_llm("How to move Oracle?", chunks, system_prompt="Custom prompt")

        assert answer == STUB_REPLY
        body = requests[0]["body"]
        assert body["messages"][0] == {"role": "system", "content": "Custom prompt"}
        user = body["messages"][1]["content"]
        assert "How to move Oracle?" in user
        assert "chunk-9" in user and "chunk-10" not in user  # context capped at 10 chunks
        assert recorded_calls[0]["operation"] == "chat"

    def test_provider_failure_returns_safe_message(self, clean_llm_env):
        clean_llm_env.setenv("OPENAI_API_KEY", "sk-test")
        with patch.object(llm_service, "get_llm", side_effect=RuntimeError("secret internals")):
            answer = llm_service.summarize_with_llm("q", ["ctx"])
        assert answer.startswith("LLM error")
        assert "secret internals" not in answer  # no stack/internal leakage to the client
