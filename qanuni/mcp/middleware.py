"""HTTP governance middleware for the Qanuni MCP server."""

from __future__ import annotations

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from qanuni.core.exceptions import ErrorCode
from qanuni.mcp.audit import QanuniMcpAuditLogger
from qanuni.mcp.models import McpAuditEvent, QanuniMcpServerSettings
from qanuni.mcp.rate_limit import InMemoryRateLimiter


class QanuniMcpGovernanceMiddleware(BaseHTTPMiddleware):
    """Apply bearer auth and rate limiting before MCP traffic reaches the server.

    Args:
        app: Wrapped ASGI application.
        settings: Resolved MCP server settings.
        rate_limiter: Shared in-memory rate limiter.
        audit_logger: Audit logger used for denied-request events.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: QanuniMcpServerSettings,
        rate_limiter: InMemoryRateLimiter,
        audit_logger: QanuniMcpAuditLogger,
    ) -> None:
        """Store the governance collaborators used for each HTTP request.

        Args:
            app: Wrapped ASGI application.
            settings: Resolved MCP server settings.
            rate_limiter: Shared in-memory rate limiter.
            audit_logger: Audit logger used for denied-request events.

        Returns:
            None.

        Raises:
            None.
        """
        super().__init__(app)
        self._settings: QanuniMcpServerSettings = settings
        self._rate_limiter: InMemoryRateLimiter = rate_limiter
        self._audit_logger: QanuniMcpAuditLogger = audit_logger
        self._mount_path: str = settings.normalized_mount_path()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Authorize and rate-limit one incoming HTTP request.

        Args:
            request: Incoming Starlette request.
            call_next: Downstream application dispatcher provided by Starlette.

        Returns:
            The downstream HTTP response or an early denial response.

        Raises:
            None.
        """
        if not request.url.path.startswith(self._mount_path):
            return await call_next(request)
        if (
            request.url.path == "/healthz"
            and self._settings.expose_healthcheck_without_auth
        ):
            return await call_next(request)

        principal: str
        if self._settings.require_auth:
            principal = self._validate_bearer_identity(request)
            if not principal:
                return self._deny(
                    status_code=401,
                    error_code=ErrorCode.MCP_AUTH_REQUIRED,
                    message="Missing or invalid bearer token for the Qanuni MCP server.",
                    target=request.url.path,
                )
        else:
            principal = "anonymous"

        decision = self._rate_limiter.check(principal)
        if not decision.allowed:
            return self._deny(
                status_code=429,
                error_code=ErrorCode.MCP_RATE_LIMITED,
                message="The Qanuni MCP request budget has been exceeded for this caller.",
                target=request.url.path,
                actor=principal,
                extra_headers={
                    "Retry-After": str(decision.retry_after_seconds),
                    "X-RateLimit-Remaining": "0",
                },
            )

        request.state.qanuni_principal = principal
        response: Response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        return response

    def _validate_bearer_identity(self, request: Request) -> str:
        """Return a stable principal hash when the bearer token is valid.

        Args:
            request: Incoming Starlette request containing HTTP headers.

        Returns:
            A stable principal label derived from the bearer token, or an empty string.

        Raises:
            None.
        """
        header_value: str | None = request.headers.get("authorization")
        expected_token: str | None = self._settings.auth_token_value()
        if header_value is None or expected_token is None:
            return ""
        prefix: str = "Bearer "
        if not header_value.startswith(prefix):
            return ""
        received_token: str = header_value[len(prefix) :].strip()
        if received_token != expected_token:
            return ""
        token_hash: str = hashlib.sha256(received_token.encode("utf-8")).hexdigest()[:12]
        return f"bearer:{token_hash}"

    def _deny(
        self,
        *,
        status_code: int,
        error_code: ErrorCode,
        message: str,
        target: str,
        actor: str = "unknown",
        extra_headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        """Build a denial response and persist a matching audit event.

        Args:
            status_code: HTTP status code used for the denial response.
            error_code: Stable machine-readable Qanuni error code.
            message: Human-readable denial reason.
            target: Request path or target surface associated with the denial.
            actor: Stable actor label, if known.
            extra_headers: Optional HTTP headers to attach to the denial response.

        Returns:
            A JSON denial response ready for immediate return.

        Raises:
            None.
        """
        self._audit_logger.log(
            McpAuditEvent(
                event_id=f"audit_{hashlib.sha1(f'{actor}:{target}:{status_code}'.encode()).hexdigest()[:16]}",
                actor=actor,
                action="http_request_denied",
                target=target,
                status="denied",
                metadata={"status_code": status_code, "error_code": error_code.value},
            )
        )
        response: JSONResponse = JSONResponse(
            {
                "message": message,
                "error_code": error_code.value,
                "details": {"target": target},
            },
            status_code=status_code,
        )
        if extra_headers is not None:
            header_name: str
            header_value: str
            for header_name, header_value in extra_headers.items():
                response.headers[header_name] = header_value
        return response
