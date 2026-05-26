"""Typed observability models for Phase 6 hardening."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ObservabilityEvent(BaseModel):
    """Represent one structured runtime event emitted by Qanuni.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    event_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scope_type: Literal["tool", "workflow"]
    scope_id: str
    status: Literal["success", "failure"]
    model: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    cache_status: Literal["hit", "miss", "bypass"] | None = None
    error_code: str | None = None
    failure_mode: str | None = None
    prompt_version: str | None = None
    prompt_asset_hash: str | None = None
    legal_reference_profile_id: str | None = None
    legal_reference_asset_hash: str | None = None
    logic_asset_hash: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RuntimeMetrics(BaseModel):
    """Store normalized metrics that can be attached to tools or workflows.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    model_used: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    prompt_version: str | None = None
    prompt_asset_hash: str | None = None
    legal_reference_asset_hash: str | None = None
    logic_asset_hash: str | None = None
    cache_hit: bool = False
    cache_key: str | None = None
