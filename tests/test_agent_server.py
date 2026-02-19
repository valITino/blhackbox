"""Tests for the BaseAgentServer FastAPI agent containers.

Each agent runs as a separate Docker container with a FastAPI server.
These tests verify the server creation, routing, and Ollama integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from blhackbox.agents.base_agent_server import BaseAgentServer, ProcessRequest

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

        mock_ollama_response = {
            "message": {
                "content": '{"hosts": [], "subdomains": ["test.example.com"]}'
            }
        }

        with patch("blhackbox.agents.base_agent_server.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_ollama_response
            mock_resp.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_resp

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

        mock_ollama_response = {"message": {"content": ""}}

        with patch("blhackbox.agents.base_agent_server.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_ollama_response
            mock_resp.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_resp

            response = client.post("/process", json={
                "data": "test",
                "session_id": "s1",
                "target": "t1",
            })
            assert response.status_code == 200
            assert response.json() == {}


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
