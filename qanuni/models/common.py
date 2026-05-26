"""Shared model primitives used across tool categories."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from qanuni.ontology.models import (
    EvidenceItem,
    LegalFinding,
    LegalReferenceRecord,
    PartyRecord,
    RecommendedAction,
    TimelineEvent,
)


class ToolRuntimeConfig(BaseModel):
    """Store per-call provider overrides.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    model: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)
    api_retries: int | None = Field(default=None, ge=0)
    max_output_tokens: int | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    verbosity: Literal["low", "medium", "high"] | None = None


class BaseResult(BaseModel):
    """Store shared metadata attached to every tool result.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    tool_id: str = ""
    execution_time_ms: int = 0
    tokens_used: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    model_used: str | None = None
    timestamp: datetime | None = None
    cache_hit: bool = False
    cache_key: str | None = None
    prompt_version: str | None = None
    prompt_asset_hash: str | None = None
    legal_reference_asset_hash: str | None = None
    logic_asset_hash: str | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    legal_reference_profile_id: str | None = None
    legal_reference_source_ids: list[str] = Field(default_factory=list)
    legal_reference_rule_ids: list[str] = Field(default_factory=list)
    legal_references: list[LegalReferenceRecord] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    findings: list[LegalFinding] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    affected_parties: list[PartyRecord] = Field(default_factory=list)
    timeline_events: list[TimelineEvent] = Field(default_factory=list)


class CalculationStep(BaseModel):
    """Represents a single monetary calculation step."""

    description: str
    amount: float = Field(ge=0)


class LegalIssue(BaseModel):
    """Describes a legal issue identified by a tool."""

    title: str
    severity: Literal["low", "medium", "high", "critical"]
    explanation: str
    recommendation: str


class ContractGap(BaseModel):
    """Represents a specific gap in a contract."""

    clause: str
    severity: Literal["low", "medium", "high", "critical"]
    recommendation: str


class AmbiguousClause(BaseModel):
    """Captures wording that needs clarification or rewrite."""

    excerpt: str
    reason: str
    suggested_rewrite: str


class TextChange(BaseModel):
    """Represents a before-and-after drafting improvement."""

    original: str
    improved: str
    reason: str


class KeyDate(BaseModel):
    """Represents a date surfaced from a legal document."""

    label: str
    value: str


class PDPLRight(BaseModel):
    """Represents whether a PDPL right is covered in a document."""

    right_name: str
    covered: bool
    note: str
