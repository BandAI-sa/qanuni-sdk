"""CLI entrypoint for serving the optional Qanuni MCP server."""

from __future__ import annotations

import typer

from qanuni.client import LegalClient
from qanuni.mcp.models import QanuniMcpServerSettings
from qanuni.mcp.server import create_mcp_app

app = typer.Typer(add_completion=False, help="Serve the curated Qanuni MCP server.")


@app.command()
def serve(
    host: str | None = typer.Option(
        default=None,
        help="Optional host override for the MCP server.",
    ),
    port: int | None = typer.Option(
        default=None,
        help="Optional port override for the MCP server.",
    ),
) -> None:
    """Serve the curated Qanuni MCP app over Streamable HTTP.

    Args:
        host: Optional host override for the MCP server.
        port: Optional port override for the MCP server.

    Returns:
        None.

    Raises:
        RuntimeError: If the optional MCP server dependencies are not installed.
    """
    import uvicorn

    settings: QanuniMcpServerSettings = QanuniMcpServerSettings()
    if host is not None:
        settings.host = host
    if port is not None:
        settings.port = port

    app_instance = create_mcp_app(
        client=LegalClient(),
        settings=settings,
    )
    uvicorn.run(app_instance, host=settings.host, port=settings.port, log_level="warning")


def main() -> None:
    """Run the Typer-based MCP server CLI.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: When the CLI completes or fails.
    """
    app()
