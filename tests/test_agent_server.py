"""Tests for the BaseAgentServer FastAPI agent containers.

Each agent runs as a separate Docker container with a FastAPI server.
These tests verify the server creation, routing, and Ollama integration
via the official ``ollama`` Python package.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from ollama import ResponseError

from blhackbox.agents.base_agent_server import (
    BaseAgentServer,
    ProcessRequest,
    _serialize_data,
)

# ---------------------------------------------------------------------------
# BaseAgentServer creation
# ---------------------------------------------------------------------------


class TestBaseAgentServer:
    def test_creates_fastapi_app(self) -> None:
        server = BaseAgentServer("ingestionagent")
        assert server.app is not None
        assert server.agent_name == "ingestionagent"

    def test_loads_prompt_from_file(self) -> None:
        server = BaseAgentServer("ingestionagent")
        assert "ingestion" in server.system_prompt.lower()
        assert "json" in server.system_prompt.lower()

    def test_fallback_prompt_for_unknown_agent(self) -> None:
        server = BaseAgentServer("nonexistentagent")
        assert "nonexistentagent" in server.system_prompt
        assert "JSON" in server.system_prompt

    def test_all_agent_prompts_load(self) -> None:
        for name in ("ingestionagent", "processingagent", "synthesisagent"):
            server = BaseAgentServer(name)
            assert len(server.system_prompt) > 50, f"Prompt for {name} too short"


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        server = BaseAgentServer("ingestionagent")
        client = TestClient(server.app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["agent"] == "ingestionagent"


# ---------------------------------------------------------------------------
# Process endpoint
# ---------------------------------------------------------------------------


class TestProcessEndpoint:
    def test_process_with_mock_ollama(self) -> None:
        server = BaseAgentServer("ingestionagent")
        client = TestClient(server.app)

        mock_response = SimpleNamespace(
            message=SimpleNamespace(
                content='{"hosts": [], "subdomains": ["test.example.com"]}'
            )
        )

        mock_ollama_client = AsyncMock()
        mock_ollama_client.chat.return_value = mock_response

        with patch(
            "blhackbox.agents.base_agent_server.AsyncClient",
            return_value=mock_ollama_client,
        ):
            response = client.post("/process", json={
                "data": "nmap output",
                "session_id": "test-session",
                "target": "example.com",
            })
            assert response.status_code == 200
            assert response.json()["subdomains"] == ["test.example.com"]

    def test_process_empty_ollama_response(self) -> None:
        server = BaseAgentServer("ingestionagent")
        client = TestClient(server.app)

        mock_response = SimpleNamespace(
            message=SimpleNamespace(content="")
        )

        mock_ollama_client = AsyncMock()
        mock_ollama_client.chat.return_value = mock_response

        with patch(
            "blhackbox.agents.base_agent_server.AsyncClient",
            return_value=mock_ollama_client,
        ):
            response = client.post("/process", json={
                "data": "test",
                "session_id": "s1",
                "target": "t1",
            })
            assert response.status_code == 502
            assert "empty response" in response.json()["detail"]

    def test_process_none_content(self) -> None:
        server = BaseAgentServer("ingestionagent")
        client = TestClient(server.app)

        mock_response = SimpleNamespace(
            message=SimpleNamespace(content=None)
        )

        mock_ollama_client = AsyncMock()
        mock_ollama_client.chat.return_value = mock_response

        with patch(
            "blhackbox.agents.base_agent_server.AsyncClient",
            return_value=mock_ollama_client,
        ):
            response = client.post("/process", json={
                "data": "test",
                "session_id": "s1",
                "target": "t1",
            })
            assert response.status_code == 502
            assert "empty response" in response.json()["detail"]


# ---------------------------------------------------------------------------
# ProcessRequest model
# ---------------------------------------------------------------------------


class TestProcessRequest:
    def test_dict_data(self) -> None:
        req = ProcessRequest(data={"key": "value"}, session_id="s1", target="t1")
        assert req.data == {"key": "value"}

    def test_string_data(self) -> None:
        req = ProcessRequest(data="raw text", session_id="s1", target="t1")
        assert req.data == "raw text"

    def test_defaults(self) -> None:
        req = ProcessRequest(data="test")
        assert req.session_id == ""
        assert req.target == ""


# ---------------------------------------------------------------------------
# _serialize_data — ensures dicts become valid JSON, not Python repr
# ---------------------------------------------------------------------------


class TestSerializeData:
    def test_string_passthrough(self) -> None:
        """String data is returned as-is."""
        assert _serialize_data("raw nmap output") == "raw nmap output"

    def test_dict_becomes_json(self) -> None:
        """Dict data is serialised to valid JSON, NOT Python repr."""
        data = {"hosts": ["10.0.0.1"], "ports": [80, 443]}
        result = _serialize_data(data)
        # Must be valid JSON (str() would produce single-quoted Python repr)
        parsed = json.loads(result)
        assert parsed == data

    def test_nested_dict(self) -> None:
        data = {"ingestion_output": {"hosts": []}, "processing_output": {"findings": {}}}
        result = _serialize_data(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_empty_dict(self) -> None:
        assert _serialize_data({}) == "{}"

    def test_empty_string(self) -> None:
        assert _serialize_data("") == ""

    def test_dict_with_special_chars(self) -> None:
        """Ensure special characters are properly JSON-escaped."""
        data = {"description": 'He said "hello" & goodbye'}
        result = _serialize_data(data)
        parsed = json.loads(result)
        assert parsed["description"] == data["description"]


# ---------------------------------------------------------------------------
# Process endpoint — dict data sent as valid JSON to Ollama
# ---------------------------------------------------------------------------


class TestProcessEndpointDictData:
    def test_dict_data_sent_as_json_to_ollama(self) -> None:
        """When /process receives dict data, Ollama should get valid JSON, not repr."""
        server = BaseAgentServer("ingestionagent")
        client = TestClient(server.app)

        mock_response = SimpleNamespace(
            message=SimpleNamespace(content='{"findings": {}}')
        )

        mock_ollama_client = AsyncMock()
        mock_ollama_client.chat.return_value = mock_response

        dict_data = {"hosts": ["10.0.0.1"], "ports": [80]}

        with patch(
            "blhackbox.agents.base_agent_server.AsyncClient",
            return_value=mock_ollama_client,
        ):
            response = client.post("/process", json={
                "data": dict_data,
                "session_id": "s1",
                "target": "t1",
            })
            assert response.status_code == 200

            # Verify Ollama received valid JSON, not Python repr
            call_args = mock_ollama_client.chat.call_args
            user_content = call_args.kwargs["messages"][1]["content"]
            # Must be valid JSON
            parsed = json.loads(user_content)
            assert parsed == dict_data


# ---------------------------------------------------------------------------
# Process endpoint — retry on Ollama errors
# ---------------------------------------------------------------------------


class TestProcessEndpointRetry:
    def test_retries_on_response_error(self) -> None:
        """Agent should retry on Ollama ResponseError before returning 502."""
        server = BaseAgentServer("ingestionagent")
        client = TestClient(server.app)

        mock_ollama_client = AsyncMock()
        # ResponseError needs a specific format
        mock_ollama_client.chat.side_effect = ResponseError("model not found")

        with patch(
            "blhackbox.agents.base_agent_server.AsyncClient",
            return_value=mock_ollama_client,
        ), patch(
            "blhackbox.agents.base_agent_server.OLLAMA_RETRIES", 1,
        ), patch(
            "blhackbox.agents.base_agent_server.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            response = client.post("/process", json={
                "data": "test", "session_id": "s1", "target": "t1",
            })
            assert response.status_code == 502
            # Should have retried (1 retry = 2 total attempts)
            assert mock_ollama_client.chat.call_count == 2
            # Should have slept between retries
            mock_sleep.assert_called_once()

    def test_succeeds_after_retry(self) -> None:
        """Agent should succeed after a transient failure."""
        server = BaseAgentServer("ingestionagent")
        client = TestClient(server.app)

        mock_response = SimpleNamespace(
            message=SimpleNamespace(content='{"hosts": []}')
        )

        mock_ollama_client = AsyncMock()
        # First call fails, second succeeds
        mock_ollama_client.chat.side_effect = [
            ResponseError("transient error"),
            mock_response,
        ]

        with patch(
            "blhackbox.agents.base_agent_server.AsyncClient",
            return_value=mock_ollama_client,
        ), patch(
            "blhackbox.agents.base_agent_server.OLLAMA_RETRIES", 1,
        ), patch(
            "blhackbox.agents.base_agent_server.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            response = client.post("/process", json={
                "data": "test", "session_id": "s1", "target": "t1",
            })
            assert response.status_code == 200
            assert response.json() == {"hosts": []}


# ---------------------------------------------------------------------------
# Health endpoint — Ollama reachability
# ---------------------------------------------------------------------------


class TestHealthEndpointOllamaCheck:
    def test_health_shows_ollama_reachable(self) -> None:
        server = BaseAgentServer("ingestionagent")
        client = TestClient(server.app)

        mock_ollama_client = AsyncMock()
        mock_ollama_client.list.return_value = {"models": [{"name": "llama3.3"}]}

        with patch(
            "blhackbox.agents.base_agent_server.AsyncClient",
            return_value=mock_ollama_client,
        ):
            response = client.get("/health")
            data = response.json()
            assert data["status"] == "ok"
            assert data["ollama"] == "reachable"
            assert data["models_loaded"] == 1

    def test_health_shows_ollama_unreachable(self) -> None:
        server = BaseAgentServer("ingestionagent")
        client = TestClient(server.app)

        mock_ollama_client = AsyncMock()
        mock_ollama_client.list.side_effect = ConnectionError("unreachable")

        with patch(
            "blhackbox.agents.base_agent_server.AsyncClient",
            return_value=mock_ollama_client,
        ):
            response = client.get("/health")
            data = response.json()
            assert data["status"] == "ok"
            assert data["ollama"] == "unreachable"
