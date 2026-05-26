"""Optional MCP server exports for the Qanuni free edition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qanuni.mcp.models import QanuniMcpServerSettings

if TYPE_CHECKING:
    from qanuni.client import LegalClient


def create_mcp_server(
    *,
    client: LegalClient | None = None,
    settings: QanuniMcpServerSettings | None = None,
) -> object:
    """Create the curated FastMCP server lazily.

    Args:
        client: Optional prebuilt SDK client.
        settings: Optional prebuilt MCP settings object.

    Returns:
        A configured `FastMCP` server instance.

    Raises:
        ImportError: If the optional MCP dependency is not installed.
    """
    from qanuni.mcp.server import create_mcp_server as _create_mcp_server

    return _create_mcp_server(client=client, settings=settings)


def create_mcp_app(
    *,
    client: LegalClient | None = None,
    settings: QanuniMcpServerSettings | None = None,
) -> object:
    """Create the curated Starlette MCP app lazily.

    Args:
        client: Optional prebuilt SDK client.
        settings: Optional prebuilt MCP settings object.

    Returns:
        A configured Starlette application.

    Raises:
        ImportError: If the optional MCP dependency is not installed.
    """
    from qanuni.mcp.server import create_mcp_app as _create_mcp_app

    return _create_mcp_app(client=client, settings=settings)


__all__ = ["QanuniMcpServerSettings", "create_mcp_app", "create_mcp_server"]
