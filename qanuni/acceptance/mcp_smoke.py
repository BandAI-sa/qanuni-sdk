"""External MCP smoke test for acceptance validation."""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Literal

from qanuni.acceptance.documents import load_sample_document
from qanuni.acceptance.runner import build_acceptance_client, resolve_acceptance_artifact_paths


def main() -> None:
    """Run the external MCP smoke test CLI.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: If CLI parsing fails or MCP dependencies are unavailable.
    """
    parser = argparse.ArgumentParser(description="Run a Qanuni MCP smoke test.")
    parser.add_argument(
        "--mode",
        choices=("mocked", "live"),
        default="mocked",
        help="Whether to exercise MCP with the offline mocked provider or live OpenAI calls.",
    )
    parser.add_argument(
        "--auth-token",
        default="acceptance-token",
        help="Bearer token used to protect the local MCP endpoint during the smoke run.",
    )
    parser.add_argument(
        "--working-dir",
        help="Optional directory for cache, observability, and MCP audit artifacts.",
    )
    parser.add_argument(
        "--persist-observability",
        action="store_true",
        help="Persist observability events to disk inside the acceptance working directory.",
    )
    args = parser.parse_args()

    report = run_mcp_smoke(
        mode=args.mode,
        auth_token=args.auth_token,
        working_dir=Path(args.working_dir) if args.working_dir else None,
        observability_persist=args.persist_observability,
    )
    _emit_json(report)


def run_mcp_smoke(
    *,
    mode: Literal["mocked", "live"] = "mocked",
    auth_token: str = "acceptance-token",
    working_dir: Path | None = None,
    observability_persist: bool = False,
) -> dict[str, Any]:
    """Run the curated MCP smoke scenario and return a structured report.

    Args:
        mode: Whether to exercise MCP with the mocked provider or live OpenAI calls.
        auth_token: Bearer token used to protect the temporary MCP server.
        working_dir: Optional directory for cache, observability, and audit artifacts.
        observability_persist: Whether observability events should be persisted to disk.

    Returns:
        Structured MCP smoke report.

    Raises:
        RuntimeError: If live mode is requested without `OPENAI_API_KEY`.
        SystemExit: If the optional MCP dependencies are unavailable.
    """
    (
        httpx,
        uvicorn,
        ClientSession,
        streamable_http_client,
        qanuni_mcp_server_settings,
        create_mcp_app,
    ) = _import_mcp_dependencies()
    artifact_paths = resolve_acceptance_artifact_paths(working_dir)
    client = build_acceptance_client(
        mode=mode,
        cache_enabled=True,
        observability_persist=observability_persist,
        working_dir=artifact_paths.root_dir,
    )
    settings = qanuni_mcp_server_settings(
        auth_token=auth_token,
        rate_limit_max_requests=20,
        rate_limit_window_seconds=60,
        port=_find_free_port(),
        audit_log_path=artifact_paths.mcp_audit_log_path,
    )
    app = create_mcp_app(client=client, settings=settings)
    server, thread = _start_server(
        app=app,
        host=settings.host,
        port=settings.port,
        uvicorn_module=uvicorn,
    )
    try:
        result = asyncio.run(
            _exercise_mcp(
                settings=settings,
                httpx_module=httpx,
                client_session_class=ClientSession,
                streamable_http_client_factory=streamable_http_client,
            )
        )
    finally:
        server.should_exit = True
        thread.join(timeout=5)

    return {
        "mode": mode,
        "artifact_paths": artifact_paths.as_json(),
        "mcp": result,
    }


async def _exercise_mcp(
    *,
    settings: Any,
    httpx_module: Any,
    client_session_class: type[Any],
    streamable_http_client_factory: Any,
) -> dict[str, object]:
    """Call the MCP server through the official client and collect results.

    Args:
        settings: Runtime server settings used for the smoke test.
        httpx_module: Imported `httpx` module used for HTTP transport.
        client_session_class: Official MCP `ClientSession` class.
        streamable_http_client_factory: Official MCP HTTP client context manager factory.

    Returns:
        Serializable summary of MCP tool availability and outputs.

    Raises:
        Any: Re-raises client or transport failures.
    """
    base_url = f"http://{settings.host}:{settings.port}{settings.normalized_mount_path()}/"
    async with httpx_module.AsyncClient(
        headers={"Authorization": f"Bearer {settings.auth_token_value()}"},
    ) as http_client:
        async with streamable_http_client_factory(base_url, http_client=http_client) as transport:
            read_stream, write_stream, _ = transport
            async with client_session_class(read_stream, write_stream) as session:
                await session.initialize()
                listed_tools = await session.list_tools()
                tool_names = sorted(tool.name for tool in listed_tools.tools)

                contract_review = await session.call_tool(
                    "workflow_contract_review",
                    {
                        "payload": {
                            "document_text": load_sample_document("service_agreement_ar.md"),
                            "contract_type": "service_agreement",
                            "include_redlines": True,
                        }
                    },
                )
                contract_output = contract_review.structuredContent
                state_result = await session.read_resource(
                    contract_output["resource_uris"]["state_uri"]
                )

                notice = await session.call_tool(
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
                            "support_document_text": load_sample_document(
                                "prelitigation_support_ar.md"
                            ),
                            "support_document_type": "demand_support",
                        }
                    },
                )
                notice_output = notice.structuredContent

    return {
        "tool_names": tool_names,
        "contract_review_surface_id": contract_output["surface_id"],
        "contract_review_state_excerpt": state_result.contents[0].text[:280],
        "pre_litigation_surface_id": notice_output["surface_id"],
        "pre_litigation_summary": notice_output["summary"],
    }


def _import_mcp_dependencies() -> tuple[Any, Any, type[Any], Any, type[Any], Any]:
    """Import the optional MCP smoke dependencies lazily.

    Args:
        None.

    Returns:
        Imported MCP smoke collaborators used by the command.

    Raises:
        SystemExit: If the required optional dependencies are unavailable.
    """
    try:
        import httpx
        import uvicorn
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        from qanuni.mcp.models import QanuniMcpServerSettings
        from qanuni.mcp.server import create_mcp_app
    except ImportError as exc:
        raise SystemExit(
            "The MCP smoke test requires the optional MCP dependencies. "
            'Install them with: python -m pip install "qanuni-sdk[mcp]"'
        ) from exc
    return (
        httpx,
        uvicorn,
        ClientSession,
        streamable_http_client,
        QanuniMcpServerSettings,
        create_mcp_app,
    )


def _emit_json(payload: dict[str, Any]) -> None:
    """Write JSON to stdout with a UTF-8-safe fallback for Windows consoles.

    Args:
        payload: JSON-serializable payload to print.

    Returns:
        None.

    Raises:
        OSError: If stdout cannot be written.
        TypeError: If the payload is not JSON-serializable.
    """
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(rendered.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        return
    sys.stdout.write(rendered)
    sys.stdout.write("\n")


def _find_free_port() -> int:
    """Return a currently unused localhost TCP port.

    Args:
        None.

    Returns:
        Available localhost TCP port.

    Raises:
        OSError: If the operating system cannot allocate a socket.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server(
    *,
    app: object,
    host: str,
    port: int,
    uvicorn_module: Any,
) -> tuple[Any, threading.Thread]:
    """Start the MCP app in a background Uvicorn server.

    Args:
        app: ASGI app returned by `create_mcp_app`.
        host: Host where the temporary MCP server should listen.
        port: Port where the temporary MCP server should listen.
        uvicorn_module: Imported `uvicorn` module used to create the server.

    Returns:
        Running Uvicorn server and its backing thread.

    Raises:
        AssertionError: If the server does not become ready in time.
    """
    config = uvicorn_module.Config(app, host=host, port=port, log_level="error")
    server = uvicorn_module.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while time.time() < deadline:
        if server.started:
            return server, thread
        time.sleep(0.05)
    raise AssertionError("The acceptance MCP server did not start in time.")


if __name__ == "__main__":
    main()
