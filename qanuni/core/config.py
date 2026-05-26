"""Configuration model for the free Qanuni distribution."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from qanuni.models.common import ToolRuntimeConfig


class QanuniConfig(BaseSettings):
    """Store resolved SDK configuration for the free edition.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    legal_reference_catalog_dir: Path | None = Field(
        default=None,
        alias="QANUNI_LEGAL_REFERENCE_CATALOG_DIR",
    )

    model: str = Field(default="gpt-5-mini", alias="QANUNI_MODEL")
    language: str = Field(default="ar", alias="QANUNI_LANGUAGE")
    jurisdiction: str = Field(default="SA", alias="QANUNI_JURISDICTION")

    timeout: int = Field(default=60, alias="QANUNI_TIMEOUT")
    max_retries: int = Field(default=0, alias="QANUNI_MAX_RETRIES")
    max_output_tokens: int | None = Field(default=None, alias="QANUNI_MAX_OUTPUT_TOKENS")
    temperature: float | None = Field(default=None, alias="QANUNI_TEMPERATURE", ge=0.0, le=2.0)
    reasoning_effort: Literal["low", "medium", "high"] | None = Field(
        default=None,
        alias="QANUNI_REASONING_EFFORT",
    )
    verbosity: Literal["low", "medium", "high"] | None = Field(
        default=None,
        alias="QANUNI_VERBOSITY",
    )

    verbose: bool = Field(default=False, alias="QANUNI_VERBOSE")
    log_level: str = Field(default="WARNING", alias="QANUNI_LOG_LEVEL")
    cache_enabled: bool = Field(default=False, alias="QANUNI_CACHE_ENABLED")
    cache_dir: Path = Field(default=Path(".qanuni_cache"), alias="QANUNI_CACHE_DIR")
    cache_ttl_seconds: int = Field(default=86400, alias="QANUNI_CACHE_TTL_SECONDS", ge=1)
    observability_persist: bool = Field(
        default=False,
        alias="QANUNI_OBSERVABILITY_PERSIST",
    )
    observability_log_path: Path = Field(
        default=Path(".qanuni_observability/qanuni_events.jsonl"),
        alias="QANUNI_OBSERVABILITY_LOG_PATH",
    )
    agent_logging_enabled: bool = Field(
        default=True,
        alias="QANUNI_AGENT_LOGGING_ENABLED",
    )
    agent_log_dir: Path = Field(
        default=Path("logs/agent"),
        alias="QANUNI_AGENT_LOG_DIR",
    )
    asset_manifest_enforced: bool = Field(
        default=True,
        alias="QANUNI_ASSET_MANIFEST_ENFORCED",
    )
    model_pricing_file: Path | None = Field(
        default=None,
        alias="QANUNI_MODEL_PRICING_FILE",
    )
    tool_overrides: dict[str, ToolRuntimeConfig] = Field(default_factory=dict)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    def api_key_value(self) -> str | None:
        """Return the decrypted API key value when configured.

        Args:
            None.

        Returns:
            The decrypted API key value, or `None` when no key is configured.

        Raises:
            None.
        """
        if self.api_key is None:
            return None
        return self.api_key.get_secret_value()
