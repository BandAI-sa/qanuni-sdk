"""FastMCP server factory for the curated Qanuni Phase-5 surface."""
from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, Literal, cast

from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from qanuni.client import LegalClient
from qanuni.core.exceptions import ErrorCode, QanuniConfigError, QanuniError
from qanuni.mcp.audit import QanuniMcpAuditLogger
from qanuni.mcp.middleware import QanuniMcpGovernanceMiddleware
from qanuni.mcp.models import McpExecutionEnvelope, QanuniMcpServerSettings
from qanuni.mcp.rate_limit import InMemoryRateLimiter
from qanuni.mcp.runtime import QanuniMcpRuntime
from qanuni.mcp.surface import McpSurfaceMetadata


class QanuniMcpServerFactory:
    """Build the FastMCP server and Starlette app for Phase 5.

    Args:
        client: Shared SDK client used by the server runtime.
        settings: Resolved MCP server settings.

    Returns:
        None.

    Raises:
        QanuniConfigError: If required auth settings are missing.
    """

    def __init__(self, *, client: LegalClient, settings: QanuniMcpServerSettings) -> None:
        """Initialize the reusable collaborators for the MCP server build.

        Args:
            client: Shared SDK client used by the server runtime.
            settings: Resolved MCP server settings.

        Returns:
            None.

        Raises:
            QanuniConfigError: If required auth settings are missing.
        """
        if settings.require_auth and not settings.auth_token_value():
            raise QanuniConfigError(
                "QANUNI_MCP_AUTH_TOKEN is required when QANUNI_MCP_REQUIRE_AUTH is enabled.",
                error_code=ErrorCode.CONFIG_INVALID,
                details={"setting": "QANUNI_MCP_AUTH_TOKEN"},
            )
        self._client: LegalClient = client
        self._settings: QanuniMcpServerSettings = settings
        self._audit_logger: QanuniMcpAuditLogger = QanuniMcpAuditLogger(
            settings.audit_log_path,
        )
        self._rate_limiter: InMemoryRateLimiter = InMemoryRateLimiter(
            window_seconds=settings.rate_limit_window_seconds,
            max_requests=settings.rate_limit_max_requests,
        )
        self._runtime: QanuniMcpRuntime = QanuniMcpRuntime(
            client,
            audit_logger=self._audit_logger,
        )

    def create_server(self) -> Any:
        """Create a configured FastMCP server with curated tools and resources.

        Args:
            None.

        Returns:
            A configured `FastMCP` server instance.

        Raises:
            ImportError: If the optional MCP dependency is not installed.
        """
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(
            name="Qanuni MCP",
            instructions=(
                "خادم MCP قانوني عربي يعرّض مجموعة محدودة وناضجة من أدوات Qanuni "
                "وworkflows مراجعة العقود وخطابات المطالبة، مع موارد للمراجع "
                "القانونية والحالة الوسيطة."
            ),
            host=self._settings.host,
            port=self._settings.port,
            streamable_http_path="/",
            json_response=True,
            stateless_http=True,
            log_level=self._mcp_log_level(),
        )
        self._register_surface_tools(server)
        self._register_resources(server)
        return server

    def create_app(self) -> Starlette:
        """Create a Starlette app wrapping the FastMCP server with governance middleware.

        Args:
            None.

        Returns:
            A Starlette application ready for `uvicorn` or any ASGI host.

        Raises:
            ImportError: If the optional MCP dependency is not installed.
        """
        server: Any = self.create_server()
        mcp_app = server.streamable_http_app()
        mount_path: str = self._settings.normalized_mount_path()
        middleware: list[Middleware] = [
            Middleware(
                QanuniMcpGovernanceMiddleware,
                settings=self._settings,
                rate_limiter=self._rate_limiter,
                audit_logger=self._audit_logger,
            )
        ]

        async def healthz(_: Request) -> JSONResponse:
            return JSONResponse(
                {
                    "status": "ok",
                    "service": "qanuni-mcp",
                    "mount_path": mount_path,
                }
            )

        @asynccontextmanager
        async def lifespan(_: Starlette) -> Any:
            async with server.session_manager.run():
                yield

        return Starlette(
            debug=False,
            lifespan=lifespan,
            routes=[
                Route("/healthz", endpoint=healthz),
                Mount(mount_path, app=mcp_app),
            ],
            middleware=middleware,
        )

    def _register_surface_tools(self, server: Any) -> None:
        """Register the curated MCP tools that invoke the runtime surfaces.

        Args:
            server: Configured `FastMCP` server receiving tool registrations.

        Returns:
            None.

        Raises:
            None.
        """
        surface: McpSurfaceMetadata
        for surface in self._runtime.list_surfaces():
            handler = self._build_surface_handler(surface)
            server.tool(
                name=surface.tool_name,
                title=surface.title,
                description=surface.description,
                meta=surface.meta_payload(),
                structured_output=True,
            )(handler)

    def _register_resources(self, server: Any) -> None:
        """Register MCP resources for legal references and persisted run state.

        Args:
            server: Configured `FastMCP` server receiving resource registrations.

        Returns:
            None.

        Raises:
            None.
        """
        @server.resource(  # type: ignore[untyped-decorator]
            "qanuni://references/catalog",
            name="qanuni_reference_catalog",
            title="فهرس الحزم المرجعية",
            description="يعرض الحزم المرجعية القانونية المكشوفة عبر سطح MCP الحالي.",
            mime_type="application/json",
        )
        def reference_catalog() -> str:
            return self._runtime.read_reference_catalog()

        @server.resource(  # type: ignore[untyped-decorator]
            "qanuni://references/{packet_key}",
            name="qanuni_reference_packet",
            title="حزمة مرجعية قانونية",
            description="يعرض حزمة مرجعية قانونية واحدة بصيغة JSON.",
            mime_type="application/json",
        )
        def reference_packet(packet_key: str) -> str:
            return self._runtime.read_reference_packet(packet_key)

        @server.resource(  # type: ignore[untyped-decorator]
            "qanuni://runs",
            name="qanuni_runs_index",
            title="فهرس التشغيلات",
            description="يعرض أحدث التشغيلات التي نفذها خادم Qanuni MCP.",
            mime_type="application/json",
        )
        def runs_index() -> str:
            return self._runtime.read_runs_index()

        @server.resource(  # type: ignore[untyped-decorator]
            "qanuni://runs/{run_id}/output",
            name="qanuni_run_output",
            title="مخرج تشغيل",
            description="يعرض الناتج الكامل لأداة أو workflow سبق تنفيذها.",
            mime_type="application/json",
        )
        def run_output(run_id: str) -> str:
            return self._runtime.read_run_output(run_id)

        @server.resource(  # type: ignore[untyped-decorator]
            "qanuni://runs/{run_id}/state",
            name="qanuni_run_state",
            title="حالة workflow",
            description="يعرض الحالة الوسيطة والنهائية لـ workflow سبق تنفيذها.",
            mime_type="application/json",
        )
        def run_state(run_id: str) -> str:
            return self._runtime.read_run_state(run_id)

        @server.resource(  # type: ignore[untyped-decorator]
            "qanuni://runs/{run_id}/findings",
            name="qanuni_run_findings",
            title="الملاحظات الوسيطة",
            description="يعرض findings المجمعة من تشغيل سابق بصورة قابلة لإعادة الاستخدام.",
            mime_type="application/json",
        )
        def run_findings(run_id: str) -> str:
            return self._runtime.read_run_findings(run_id)

        @server.resource(  # type: ignore[untyped-decorator]
            "qanuni://runs/{run_id}/artifacts/{artifact_name}",
            name="qanuni_run_artifact",
            title="مستند مولد",
            description="يعرض artifact نصيًا سبق توليده داخل workflow.",
            mime_type="text/plain",
        )
        def run_artifact(run_id: str, artifact_name: str) -> str:
            return self._runtime.read_run_artifact(run_id, artifact_name)

    def _build_surface_handler(self, surface: McpSurfaceMetadata) -> object:
        """Build one async MCP tool handler bound to a curated surface.

        Args:
            surface: Curated surface metadata entry being exposed.

        Returns:
            An async function ready for `FastMCP.tool(...)` registration.

        Raises:
            None.
        """
        from mcp.server.fastmcp import Context

        runtime: QanuniMcpRuntime = self._runtime

        async def handler(
            payload: BaseModel,
            ctx: Context[Any, Any, Any],
        ) -> McpExecutionEnvelope:
            request_id: str | None = str(ctx.request_id) if ctx.request_id is not None else None
            client_id: str | None = ctx.client_id
            principal: str | None = None
            request_object: object | None = ctx.request_context.request
            if request_object is not None:
                state_object: object = getattr(request_object, "state", SimpleNamespace())
                principal = getattr(state_object, "qanuni_principal", None)
            try:
                return await runtime.ainvoke_surface(
                    surface.surface_id,
                    payload,
                    principal=principal,
                    request_id=request_id,
                    client_id=client_id,
                )
            except QanuniError as exc:
                raise ValueError(str(exc)) from exc

        handler.__name__ = surface.tool_name
        handler.__qualname__ = surface.tool_name
        handler.__doc__ = surface.description
        handler.__annotations__ = {
            "payload": surface.input_model,
            "ctx": Context,
            "return": McpExecutionEnvelope,
        }
        return handler

    def _mcp_log_level(self) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        """Normalize the SDK log level into the literal accepted by FastMCP.

        Args:
            None.

        Returns:
            A FastMCP-compatible log-level literal.

        Raises:
            None.
        """
        normalized: str = self._client.config.log_level.upper()
        allowed_levels: set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed_levels:
            normalized = "WARNING"
        return cast(
            Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            normalized,
        )


def create_mcp_server(
    *,
    client: LegalClient | None = None,
    settings: QanuniMcpServerSettings | None = None,
) -> object:
    """Create a configured FastMCP server for the curated Qanuni surface.

    Args:
        client: Optional prebuilt SDK client. When omitted, the client is created from env.
        settings: Optional prebuilt MCP settings. When omitted, the settings are loaded from env.

    Returns:
        A configured `FastMCP` server instance.

    Raises:
        ImportError: If the optional MCP dependency is not installed.
        QanuniConfigError: If required auth settings are missing.
    """
    resolved_client: LegalClient = client or LegalClient()
    resolved_settings: QanuniMcpServerSettings = settings or QanuniMcpServerSettings()
    return QanuniMcpServerFactory(
        client=resolved_client,
        settings=resolved_settings,
    ).create_server()


def create_mcp_app(
    *,
    client: LegalClient | None = None,
    settings: QanuniMcpServerSettings | None = None,
) -> Starlette:
    """Create an ASGI app exposing the curated Qanuni FastMCP server.

    Args:
        client: Optional prebuilt SDK client. When omitted, the client is created from env.
        settings: Optional prebuilt MCP settings. When omitted, the settings are loaded from env.

    Returns:
        A Starlette application ready for an ASGI host.

    Raises:
        ImportError: If the optional MCP dependency is not installed.
        QanuniConfigError: If required auth settings are missing.
    """
    resolved_client: LegalClient = client or LegalClient()
    resolved_settings: QanuniMcpServerSettings = settings or QanuniMcpServerSettings()
    return QanuniMcpServerFactory(
        client=resolved_client,
        settings=resolved_settings,
    ).create_app()
