"""Typed models for the Qanuni MCP server surface."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class McpSurfaceKind(StrEnum):
    """Describe the type of Qanuni capability exposed through MCP.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    ATOMIC_TOOL = "atomic_tool"
    WORKFLOW = "workflow"


class McpResourceLinks(BaseModel):
    """Collect follow-up MCP resource URIs related to one execution.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    output_uri: str
    state_uri: str | None = None
    findings_uri: str | None = None
    artifact_uris: dict[str, str] = Field(default_factory=dict)
    legal_reference_uris: list[str] = Field(default_factory=list)


class McpExecutionEnvelope(BaseModel):
    """Wrap one MCP tool execution with reusable follow-up links.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    run_id: str
    surface_id: str
    tool_name: str
    kind: McpSurfaceKind
    summary: str
    output: dict[str, Any]
    resource_uris: McpResourceLinks


class McpAuditEvent(BaseModel):
    """Represent one audit-log entry emitted by the MCP server.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    event_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str
    action: str
    target: str
    status: str
    request_id: str | None = None
    client_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class McpRunRecord(BaseModel):
    """Persist one surface execution for later MCP resource reads.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    run_id: str
    surface_id: str
    tool_name: str
    kind: McpSurfaceKind
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    principal: str | None = None
    request_id: str | None = None
    client_id: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    summary: str
    state_payload: dict[str, Any] | None = None
    findings_payload: list[dict[str, Any]] = Field(default_factory=list)
    artifact_payloads: dict[str, str] = Field(default_factory=dict)
    legal_reference_packet_keys: list[str] = Field(default_factory=list)


class QanuniMcpServerSettings(BaseSettings):
    """Store configuration for the optional Qanuni MCP server.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    host: str = Field(default="127.0.0.1", alias="QANUNI_MCP_HOST")
    port: int = Field(default=8088, alias="QANUNI_MCP_PORT", ge=1, le=65535)
    mount_path: str = Field(default="/mcp", alias="QANUNI_MCP_MOUNT_PATH")
    auth_token: SecretStr | None = Field(default=None, alias="QANUNI_MCP_AUTH_TOKEN")
    require_auth: bool = Field(default=True, alias="QANUNI_MCP_REQUIRE_AUTH")
    expose_healthcheck_without_auth: bool = Field(
        default=True,
        alias="QANUNI_MCP_HEALTHCHECK_OPEN",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        alias="QANUNI_MCP_RATE_LIMIT_WINDOW_SECONDS",
        ge=1,
    )
    rate_limit_max_requests: int = Field(
        default=60,
        alias="QANUNI_MCP_RATE_LIMIT_MAX_REQUESTS",
        ge=1,
    )
    audit_log_path: Path = Field(
        default=Path(".qanuni_audit/qanuni_mcp_audit.jsonl"),
        alias="QANUNI_MCP_AUDIT_LOG_PATH",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    def auth_token_value(self) -> str | None:
        """Return the resolved bearer token when configured.

        Args:
            None.

        Returns:
            The configured bearer token, or `None` when auth is not configured.

        Raises:
            None.
        """
        if self.auth_token is None:
            return None
        return self.auth_token.get_secret_value()

    def normalized_mount_path(self) -> str:
        """Return a normalized Starlette mount path for the MCP endpoint.

        Args:
            None.

        Returns:
            A leading-slash path with no trailing slash except for the root path.

        Raises:
            None.
        """
        normalized: str = self.mount_path.strip() or "/mcp"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        if normalized != "/":
            normalized = normalized.rstrip("/")
        return normalized
