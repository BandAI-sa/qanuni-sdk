"""Structured runtime event recorder."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from qanuni.observability.models import ObservabilityEvent


class ObservabilityRecorder:
    """Persist and expose structured runtime events.

    Args:
        persist: Whether new events should be appended to disk.
        log_path: Destination JSONL path used when persistence is enabled.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, *, persist: bool, log_path: Path) -> None:
        """Initialize the recorder.

        Args:
            persist: Whether new events should be appended to disk.
            log_path: Destination JSONL path used when persistence is enabled.

        Returns:
            None.

        Raises:
            None.
        """
        self._persist = persist
        self._log_path = log_path
        self._events: list[ObservabilityEvent] = []

    def record(self, event: ObservabilityEvent) -> None:
        """Append one event to memory and optionally to disk.

        Args:
            event: Structured runtime event to store.

        Returns:
            None.

        Raises:
            None.
        """
        self._events.append(event)
        if not self._persist:
            return
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as handle:
                handle.write(event.model_dump_json(fallback=str))
                handle.write("\n")
        except OSError:
            return None

    def snapshot(self) -> list[ObservabilityEvent]:
        """Return a copy of the collected in-memory events.

        Args:
            None.

        Returns:
            A shallow copy of the collected events.

        Raises:
            None.
        """
        return list(self._events)

    def clear(self) -> None:
        """Remove in-memory events collected so far.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._events.clear()


def get_observability_recorder(*, persist: bool, log_path: Path) -> ObservabilityRecorder:
    """Return a shared recorder instance for one persistence target.

    Args:
        persist: Whether recorder instances should append events to disk.
        log_path: Destination JSONL path used when persistence is enabled.

    Returns:
        A shared `ObservabilityRecorder` instance.

    Raises:
        None.
    """
    return _get_observability_recorder_cached(
        persist=persist,
        resolved_path=str(log_path.resolve()),
    )


@lru_cache(maxsize=8)
def _get_observability_recorder_cached(
    *,
    persist: bool,
    resolved_path: str,
) -> ObservabilityRecorder:
    """Memoize recorders by persistence mode and destination path.

    Args:
        persist: Whether recorder instances should append events to disk.
        resolved_path: Absolute JSONL path used for persistence.

    Returns:
        A shared `ObservabilityRecorder` instance.

    Raises:
        None.
    """
    return ObservabilityRecorder(persist=persist, log_path=Path(resolved_path))
