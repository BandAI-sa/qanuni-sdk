"""Typed models for selective result caching."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    """Represent one cached tool or workflow payload.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    cache_key: str
    scope_type: Literal["tool", "workflow"]
    scope_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
    payload: dict[str, Any]

    @classmethod
    def from_payload(
        cls,
        *,
        cache_key: str,
        scope_type: Literal["tool", "workflow"],
        scope_id: str,
        payload: dict[str, Any],
        ttl_seconds: int,
    ) -> CacheEntry:
        """Build a cache entry with a computed expiry timestamp.

        Args:
            cache_key: Stable hashed cache key.
            scope_type: Whether the entry belongs to a tool or workflow.
            scope_id: Stable tool or workflow identifier.
            payload: JSON-serializable payload to cache.
            ttl_seconds: Time to live for the cache entry in seconds.

        Returns:
            A populated cache entry with `expires_at`.

        Raises:
            None.
        """
        created_at = datetime.now(UTC)
        return cls(
            cache_key=cache_key,
            scope_type=scope_type,
            scope_id=scope_id,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=ttl_seconds),
            payload=payload,
        )

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """Return whether the entry is expired.

        Args:
            now: Optional comparison timestamp. Defaults to current UTC time.

        Returns:
            `True` when the entry has expired.

        Raises:
            None.
        """
        effective_now = now or datetime.now(UTC)
        return effective_now >= self.expires_at
