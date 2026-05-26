"""File-backed selective cache used by tools and workflows."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from qanuni.caching.models import CacheEntry


class ResultCache:
    """Persist tool and workflow results in a small JSON cache.

    Args:
        root_dir: Root directory where cache files should be stored.
        ttl_seconds: Default time to live for new entries.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, *, root_dir: Path, ttl_seconds: int) -> None:
        """Initialize the cache.

        Args:
            root_dir: Root directory where cache files should be stored.
            ttl_seconds: Default time to live for new entries.

        Returns:
            None.

        Raises:
            None.
        """
        self._root_dir = root_dir
        self._ttl_seconds = ttl_seconds

    def build_key(self, material: dict[str, Any]) -> str:
        """Build a stable SHA-256 cache key from structured material.

        Args:
            material: JSON-serializable material that defines cache identity.

        Returns:
            A deterministic hexadecimal cache key.

        Raises:
            None.
        """
        canonical = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get_model(
        self,
        *,
        cache_key: str,
        scope_type: Literal["tool", "workflow"],
        scope_id: str,
        model: type[BaseModel],
    ) -> BaseModel | None:
        """Load one cached payload and validate it into a target model.

        Args:
            cache_key: Stable hashed cache key.
            scope_type: Whether the cache entry belongs to a tool or workflow.
            scope_id: Stable tool or workflow identifier.
            model: Pydantic model used to validate the cached payload.

        Returns:
            The validated model instance, or `None` when the entry is missing or stale.

        Raises:
            None.
        """
        entry = self._read_entry(cache_key=cache_key, scope_type=scope_type, scope_id=scope_id)
        if entry is None:
            return None
        try:
            return model.model_validate(entry.payload)
        except ValidationError:
            self.delete(cache_key=cache_key, scope_type=scope_type, scope_id=scope_id)
            return None

    def set_model(
        self,
        *,
        cache_key: str,
        scope_type: Literal["tool", "workflow"],
        scope_id: str,
        value: BaseModel,
    ) -> None:
        """Store one validated Pydantic model in the cache.

        Args:
            cache_key: Stable hashed cache key.
            scope_type: Whether the cache entry belongs to a tool or workflow.
            scope_id: Stable tool or workflow identifier.
            value: Model instance to serialize and cache.

        Returns:
            None.

        Raises:
            None.
        """
        entry = CacheEntry.from_payload(
            cache_key=cache_key,
            scope_type=scope_type,
            scope_id=scope_id,
            payload=value.model_dump(mode="json"),
            ttl_seconds=self._ttl_seconds,
        )
        path = self._entry_path(cache_key=cache_key, scope_type=scope_type, scope_id=scope_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry.model_dump_json(indent=2), encoding="utf-8")

    def delete(
        self,
        *,
        cache_key: str,
        scope_type: Literal["tool", "workflow"],
        scope_id: str,
    ) -> None:
        """Delete one cache entry when present.

        Args:
            cache_key: Stable hashed cache key.
            scope_type: Whether the cache entry belongs to a tool or workflow.
            scope_id: Stable tool or workflow identifier.

        Returns:
            None.

        Raises:
            None.
        """
        path = self._entry_path(cache_key=cache_key, scope_type=scope_type, scope_id=scope_id)
        if path.exists():
            path.unlink()

    def _read_entry(
        self,
        *,
        cache_key: str,
        scope_type: Literal["tool", "workflow"],
        scope_id: str,
    ) -> CacheEntry | None:
        """Read one cache entry and drop it if it is stale or corrupt.

        Args:
            cache_key: Stable hashed cache key.
            scope_type: Whether the cache entry belongs to a tool or workflow.
            scope_id: Stable tool or workflow identifier.

        Returns:
            A validated cache entry, or `None` when it is unavailable.

        Raises:
            None.
        """
        path = self._entry_path(cache_key=cache_key, scope_type=scope_type, scope_id=scope_id)
        if not path.exists():
            return None
        try:
            entry = CacheEntry.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError, json.JSONDecodeError):
            self.delete(cache_key=cache_key, scope_type=scope_type, scope_id=scope_id)
            return None
        if entry.is_expired():
            self.delete(cache_key=cache_key, scope_type=scope_type, scope_id=scope_id)
            return None
        return entry

    def _entry_path(
        self,
        *,
        cache_key: str,
        scope_type: Literal["tool", "workflow"],
        scope_id: str,
    ) -> Path:
        """Return the on-disk path used by one cache entry.

        Args:
            cache_key: Stable hashed cache key.
            scope_type: Whether the cache entry belongs to a tool or workflow.
            scope_id: Stable tool or workflow identifier.

        Returns:
            The full file-system path for the cache entry.

        Raises:
            None.
        """
        safe_scope_id = scope_id.replace(".", "_")
        return self._root_dir / scope_type / safe_scope_id / f"{cache_key}.json"


def get_result_cache(*, root_dir: Path, ttl_seconds: int) -> ResultCache:
    """Return a shared cache instance for one directory and TTL pair.

    Args:
        root_dir: Root directory where cache files should be stored.
        ttl_seconds: Default time to live for new entries.

    Returns:
        A shared `ResultCache` instance.

    Raises:
        None.
    """
    return _get_result_cache_cached(
        resolved_dir=str(root_dir.resolve()),
        ttl_seconds=ttl_seconds,
    )


@lru_cache(maxsize=8)
def _get_result_cache_cached(*, resolved_dir: str, ttl_seconds: int) -> ResultCache:
    """Memoize cache instances by directory and TTL.

    Args:
        resolved_dir: Absolute cache directory.
        ttl_seconds: Default time to live for new entries.

    Returns:
        A shared `ResultCache` instance.

    Raises:
        None.
    """
    return ResultCache(root_dir=Path(resolved_dir), ttl_seconds=ttl_seconds)
