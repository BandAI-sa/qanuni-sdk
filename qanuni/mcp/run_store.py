"""In-memory execution store backing MCP run resources."""

from __future__ import annotations

from threading import Lock

from qanuni.core.exceptions import ErrorCode, QanuniValidationError
from qanuni.mcp.models import McpRunRecord


class QanuniMcpRunStore:
    """Persist recent MCP executions for later resource access.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self) -> None:
        """Initialize an empty thread-safe run store.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._records: dict[str, McpRunRecord] = {}
        self._lock: Lock = Lock()

    def save(self, record: McpRunRecord) -> McpRunRecord:
        """Persist one run record and return it unchanged.

        Args:
            record: Fully materialized run record to persist.

        Returns:
            The same run record after persistence.

        Raises:
            None.
        """
        with self._lock:
            self._records[record.run_id] = record
        return record

    def get(self, run_id: str) -> McpRunRecord:
        """Return one persisted run record by identifier.

        Args:
            run_id: Stable execution identifier returned by one MCP tool call.

        Returns:
            The matching persisted run record.

        Raises:
            QanuniValidationError: If the requested run does not exist.
        """
        with self._lock:
            record: McpRunRecord | None = self._records.get(run_id)
        if record is None:
            raise QanuniValidationError(
                f"MCP run '{run_id}' was not found.",
                error_code=ErrorCode.MCP_RUN_NOT_FOUND,
                details={"run_id": run_id},
            )
        return record

    def list_recent(self, *, limit: int = 50) -> list[McpRunRecord]:
        """Return the most recent persisted run records.

        Args:
            limit: Maximum number of records to return, ordered from newest to oldest.

        Returns:
            A list of recent run records.

        Raises:
            None.
        """
        with self._lock:
            records: list[McpRunRecord] = list(self._records.values())
        records.sort(key=lambda item: item.created_at, reverse=True)
        return records[:limit]
