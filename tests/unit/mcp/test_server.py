from __future__ import annotations

import asyncio
import socket
import threading
import time

import httpx
import uvicorn
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.testclient import TestClient

from qanuni.client import LegalClient
from qanuni.mcp.models import QanuniMcpServerSettings
from qanuni.mcp.server import create_mcp_app
from tests.conftest import FakeProvider


def test_governance_middleware_enforces_auth_and_rate_limit(tmp_path) -> None:
    client = LegalClient(provider_factory=FakeProvider)
    settings = QanuniMcpServerSettings(
        auth_token="test-token",
        rate_limit_max_requests=1,
        rate_limit_window_seconds=60,
        audit_log_path=tmp_path / "audit.jsonl",
    )
    app = create_mcp_app(client=client, settings=settings)

    with TestClient(app, base_url=f"http://{settings.host}:{settings.port}") as test_client:
        health = test_client.get("/healthz")
        assert health.status_code == 200

        unauthenticated = test_client.post("/mcp/", json={})
        assert unauthenticated.status_code == 401
        assert unauthenticated.json()["error_code"] == "QANUNI_MCP_AUTH_REQUIRED"

        authorized_headers = {"Authorization": "Bearer test-token"}
        first = test_client.post("/mcp/", headers=authorized_headers, json={})
        assert first.status_code in {400, 405, 406, 422}

        second = test_client.post("/mcp/", headers=authorized_headers, json={})
        assert second.status_code == 429
        assert second.json()["error_code"] == "QANUNI_MCP_RATE_LIMITED"


def test_official_mcp_client_can_run_contract_review_and_notice_workflow(
    tmp_path,
) -> None:
    client = LegalClient(provider_factory=FakeProvider)
    settings = QanuniMcpServerSettings(
        auth_token="stream-token",
        rate_limit_max_requests=20,
        rate_limit_window_seconds=60,
        audit_log_path=tmp_path / "audit.jsonl",
        port=_find_free_port(),
    )
    app = create_mcp_app(client=client, settings=settings)
    server, thread = _start_server(app=app, host=settings.host, port=settings.port)

    try:
        asyncio.run(_exercise_streamable_http_client(settings))
    finally:
        server.should_exit = True
        thread.join(timeout=5)


async def _exercise_streamable_http_client(settings: QanuniMcpServerSettings) -> None:
    base_url = f"http://{settings.host}:{settings.port}{settings.normalized_mount_path()}/"
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {settings.auth_token_value()}"},
    ) as http_client:
        async with streamable_http_client(base_url, http_client=http_client) as transport:
            read_stream, write_stream, _ = transport
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools_result = await session.list_tools()
                tool_names = {tool.name for tool in tools_result.tools}

                assert "workflow_contract_review" in tool_names
                assert "workflow_pre_litigation_notice" in tool_names

                contract_review_result = await session.call_tool(
                    "workflow_contract_review",
                    {
                        "payload": {
                            "document_text": (
                                "يلتزم الطرف الثاني بتنفيذ الأعمال، ويتم السداد لاحقًا، "
                                "ويجوز إنهاء العقد عند الحاجة."
                            ),
                            "include_redlines": True,
                        }
                    },
                )
                contract_review_output = contract_review_result.structuredContent
                assert contract_review_output["surface_id"] == "workflow.contract_review"

                state_uri = contract_review_output["resource_uris"]["state_uri"]
                state_result = await session.read_resource(state_uri)
                state_text = state_result.contents[0].text
                assert '"workflow_id": "workflow.contract_review"' in state_text

                notice_result = await session.call_tool(
                    "workflow_pre_litigation_notice",
                    {
                        "payload": {
                            "sender_name": "شركة ألف",
                            "recipient_name": "شركة باء",
                            "claim_type": "مستحقات تعاقدية",
                            "claim_amount": 85000,
                            "incident_description": "تأخر في سداد مستحقات عقد خدمات تقنية.",
                            "deadline_days": 7,
                            "threat_of_action": (
                                "سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد."
                            ),
                            "support_document_text": (
                                "أبرم الطرفان عقد خدمات تقنية ولم يتم سداد الفاتورة الأخيرة."
                            ),
                        }
                    },
                )
                notice_output = notice_result.structuredContent
                assert notice_output["surface_id"] == "workflow.pre_litigation_notice"
                assert "demand_letter_text" in notice_output["output"]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server(*, app, host: str, port: int) -> tuple[uvicorn.Server, threading.Thread]:
    config = uvicorn.Config(app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while time.time() < deadline:
        if server.started:
            return server, thread
        time.sleep(0.05)

    raise AssertionError("Uvicorn MCP server did not start within the expected timeout.")
