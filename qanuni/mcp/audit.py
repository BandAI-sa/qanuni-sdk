"""Audit logging utilities for the Qanuni MCP server."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from qanuni.mcp.models import McpAuditEvent


class QanuniMcpAuditLogger:
    """Write append-only JSONL audit events for MCP activity.

    Args:
        path: Destination JSONL file used for audit persistence.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, path: Path) -> None:
        """Store the destination path and initialize a write lock.

        Args:
            path: Destination JSONL file used for audit persistence.

        Returns:
            None.

        Raises:
            None.
        """
        self._path: Path = path
        self._lock: Lock = Lock()

    def log(self, event: McpAuditEvent) -> None:
        """Append one audit event as a UTF-8 JSONL record.

        Args:
            event: Structured audit event to append.

        Returns:
            None.

        Raises:
            OSError: If the audit-log file cannot be written.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        serialized: str = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        with self._lock:
            with self._path.open("a", encoding="utf-8") as file_handle:
                file_handle.write(serialized)
                file_handle.write("\n")
