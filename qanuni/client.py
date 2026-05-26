"""Main client entrypoint for the free Qanuni SDK distribution."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

from qanuni.agent import AgentRuntime
from qanuni.caching import ResultCache, get_result_cache
from qanuni.catalog import ToolAccessStatus, ToolMetadata, list_tools
from qanuni.core.config import QanuniConfig
from qanuni.governance import validate_asset_manifest
from qanuni.observability import (
    ModelPricingCatalog,
    ObservabilityRecorder,
    get_observability_recorder,
    load_pricing_catalog,
)
from qanuni.providers.base_provider import BaseProvider
from qanuni.providers.openai_provider import OpenAIProvider
from qanuni.tools.compliance import ComplianceTools
from qanuni.tools.contracts import ContractTools
from qanuni.tools.drafting import DraftingTools
from qanuni.tools.labor import LaborTools
from qanuni.tools.legal import LegalTools
from qanuni.tools.policies import PolicyTools
from qanuni.workflows import WorkflowTools


class LegalClient:
    """Expose the public SDK namespaces used by application developers.

    Args:
        provider_factory: Optional zero-argument callable that returns a provider instance.
        **kwargs: Direct configuration overrides forwarded into `QanuniConfig`.

    Returns:
        None.

    Raises:
        QanuniConfigError: If the provided configuration is invalid.
    """

    def __init__(
        self,
        *,
        provider_factory: Callable[[], BaseProvider] | None = None,
        **kwargs: Any,
    ) -> None:
        """Create a Qanuni client from direct keyword configuration.

        Args:
            provider_factory: Optional zero-argument callable that returns a provider instance.
            **kwargs: Direct configuration overrides forwarded into `QanuniConfig`.

        Returns:
            None.

        Raises:
            QanuniConfigError: If the provided configuration is invalid.
        """
        self._config = QanuniConfig(**kwargs)
        if self._config.asset_manifest_enforced:
            validate_asset_manifest()
        self._provider_factory: Callable[[], BaseProvider] | None = provider_factory
        self._provider: BaseProvider | None = None
        self._observability: ObservabilityRecorder | None = None
        self._pricing_catalog: ModelPricingCatalog | None = None
        self._result_cache: ResultCache | None = None
        self._labor: LaborTools | None = None
        self._contracts: ContractTools | None = None
        self._compliance: ComplianceTools | None = None
        self._drafting: DraftingTools | None = None
        self._legal: LegalTools | None = None
        self._policies: PolicyTools | None = None
        self._workflow: WorkflowTools | None = None
        self._agent: AgentRuntime | None = None

    @classmethod
    def from_config(cls, path: str | Path) -> LegalClient:
        """Create a client from a YAML configuration file.

        Args:
            path: File-system path to a `.qanuni.yaml`-style configuration file.

        Returns:
            A fully initialized `LegalClient`.

        Raises:
            OSError: If the configuration file cannot be read.
            yaml.YAMLError: If the configuration file contains invalid YAML.
        """
        config_path = Path(path)
        raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

        data: dict[str, Any] = {
            "api_key": raw.get("openai", {}).get("api_key") or raw.get("api_key"),
            "legal_reference_catalog_dir": (
                raw.get("qanuni", {}).get("legal_reference_catalog_dir")
                or raw.get("legal_reference_catalog_dir")
            ),
            "model": raw.get("openai", {}).get("model", raw.get("model", "gpt-5-mini")),
            "language": raw.get("locale", {}).get("language", raw.get("language", "ar")),
            "jurisdiction": raw.get("locale", {}).get(
                "jurisdiction", raw.get("jurisdiction", "SA")
            ),
            "timeout": raw.get("performance", {}).get("timeout", raw.get("timeout", 60)),
            "max_retries": raw.get("performance", {}).get(
                "max_retries", raw.get("max_retries", 0)
            ),
            "max_output_tokens": raw.get("openai", {}).get(
                "max_tokens", raw.get("max_output_tokens")
            ),
            "temperature": raw.get("openai", {}).get(
                "temperature", raw.get("temperature")
            ),
            "reasoning_effort": raw.get("openai", {}).get(
                "reasoning_effort", raw.get("reasoning_effort")
            ),
            "verbosity": raw.get("openai", {}).get(
                "verbosity", raw.get("verbosity")
            ),
            "verbose": raw.get("logging", {}).get("verbose", raw.get("verbose", False)),
            "log_level": raw.get("logging", {}).get("level", raw.get("log_level", "WARNING")),
            "cache_enabled": raw.get("performance", {}).get(
                "cache_enabled", raw.get("cache_enabled", False)
            ),
            "cache_dir": raw.get("performance", {}).get(
                "cache_dir", raw.get("cache_dir", ".qanuni_cache")
            ),
            "cache_ttl_seconds": raw.get("performance", {}).get(
                "cache_ttl_seconds", raw.get("cache_ttl_seconds", 86400)
            ),
            "observability_persist": raw.get("logging", {}).get(
                "observability_persist",
                raw.get("observability_persist", False),
            ),
            "observability_log_path": raw.get("logging", {}).get(
                "observability_log_path",
                raw.get("observability_log_path", ".qanuni_observability/qanuni_events.jsonl"),
            ),
            "agent_logging_enabled": raw.get("logging", {}).get(
                "agent_logging_enabled",
                raw.get("agent_logging_enabled", True),
            ),
            "agent_log_dir": raw.get("logging", {}).get(
                "agent_log_dir",
                raw.get("agent_log_dir", "logs/agent"),
            ),
            "asset_manifest_enforced": raw.get("qanuni", {}).get(
                "asset_manifest_enforced",
                raw.get("asset_manifest_enforced", True),
            ),
            "model_pricing_file": raw.get("performance", {}).get(
                "model_pricing_file",
                raw.get("model_pricing_file"),
            ),
            "tool_overrides": raw.get("tools", {}),
        }
        return cls(**data)

    @property
    def config(self) -> QanuniConfig:
        """Return the effective resolved SDK configuration.

        Args:
            None.

        Returns:
            The resolved SDK configuration object.

        Raises:
            None.
        """
        return self._config

    def get_provider(self) -> BaseProvider:
        """Lazily construct and reuse the configured provider instance.

        Args:
            None.

        Returns:
            The configured provider instance.

        Raises:
            QanuniConfigError: If the provider cannot be created from current settings.
        """
        if self._provider is None:
            if self._provider_factory is not None:
                self._provider = self._provider_factory()
            else:
                self._provider = OpenAIProvider(self._config)
        return self._provider

    @property
    def observability(self) -> ObservabilityRecorder:
        """Return the shared observability recorder.

        Args:
            None.

        Returns:
            The shared runtime event recorder.

        Raises:
            None.
        """
        if self._observability is None:
            self._observability = get_observability_recorder(
                persist=self._config.observability_persist,
                log_path=self._config.observability_log_path,
            )
        return self._observability

    @property
    def pricing_catalog(self) -> ModelPricingCatalog:
        """Return the shared pricing catalog used for cost estimation.

        Args:
            None.

        Returns:
            The loaded pricing catalog, which may be empty.

        Raises:
            OSError: If the configured pricing file cannot be read.
            ValueError: If the configured pricing file format is unsupported.
        """
        if self._pricing_catalog is None:
            self._pricing_catalog = load_pricing_catalog(self._config.model_pricing_file)
        return self._pricing_catalog

    @property
    def result_cache(self) -> ResultCache:
        """Return the shared selective result cache.

        Args:
            None.

        Returns:
            The shared file-backed result cache.

        Raises:
            None.
        """
        if self._result_cache is None:
            self._result_cache = get_result_cache(
                root_dir=self._config.cache_dir,
                ttl_seconds=self._config.cache_ttl_seconds,
            )
        return self._result_cache

    def list_tools(
        self,
        *,
        tier: Literal["free", "pro"] | None = None,
        namespace: str | None = None,
        category: str | None = None,
    ) -> list[ToolMetadata]:
        """List implemented tools available in the current SDK build.

        Args:
            tier: Optional commercial tier filter.
            namespace: Optional top-level namespace filter.
            category: Optional product-category filter.

        Returns:
            A list of implemented tool metadata records.

        Raises:
            None.
        """
        return list_tools(tier=tier, namespace=namespace, category=category)

    def list_tool_access(
        self,
        *,
        tier: Literal["free", "pro"] | None = None,
        namespace: str | None = None,
        category: str | None = None,
    ) -> list[ToolAccessStatus]:
        """List implemented tools together with current access availability.

        Args:
            tier: Optional commercial tier filter.
            namespace: Optional top-level namespace filter.
            category: Optional product-category filter.

        Returns:
            A list of tool records annotated with current access status.

        Raises:
            None.
        """
        return [
            ToolAccessStatus(
                tool_id=tool_record.tool_id,
                namespace=tool_record.namespace,
                category=tool_record.category,
                tier=tool_record.tier,
                description=tool_record.description,
                implementation=tool_record.implementation,
                available=True,
                reason=None,
            )
            for tool_record in list_tools(
                tier=tier,
                namespace=namespace,
                category=category,
            )
        ]

    @property
    def labor(self) -> LaborTools:
        """Access labor-law tools.

        Args:
            None.

        Returns:
            The lazily initialized labor namespace.

        Raises:
            QanuniConfigError: If provider construction fails during lazy initialization.
        """
        if self._labor is None:
            self._labor = LaborTools(self._config, self.get_provider)
        return self._labor

    @property
    def contracts(self) -> ContractTools:
        """Access contract and commercial tools.

        Args:
            None.

        Returns:
            The lazily initialized contracts namespace.

        Raises:
            QanuniConfigError: If provider construction fails during lazy initialization.
        """
        if self._contracts is None:
            self._contracts = ContractTools(self._config, self.get_provider)
        return self._contracts

    @property
    def compliance(self) -> ComplianceTools:
        """Access compliance and regulatory tools.

        Args:
            None.

        Returns:
            The lazily initialized compliance namespace.

        Raises:
            QanuniConfigError: If provider construction fails during lazy initialization.
        """
        if self._compliance is None:
            self._compliance = ComplianceTools(self._config, self.get_provider)
        return self._compliance

    @property
    def drafting(self) -> DraftingTools:
        """Access legal drafting and analysis tools.

        Args:
            None.

        Returns:
            The lazily initialized drafting namespace.

        Raises:
            QanuniConfigError: If provider construction fails during lazy initialization.
        """
        if self._drafting is None:
            self._drafting = DraftingTools(self._config, self.get_provider)
        return self._drafting

    @property
    def legal(self) -> LegalTools:
        """Access atomic legal extraction tools.

        Args:
            None.

        Returns:
            The lazily initialized legal namespace.

        Raises:
            QanuniConfigError: If provider construction fails during lazy initialization.
        """
        if self._legal is None:
            self._legal = LegalTools(self._config, self.get_provider)
        return self._legal

    @property
    def policies(self) -> PolicyTools:
        """Access policies and HR-document tools.

        Args:
            None.

        Returns:
            The lazily initialized policies namespace.

        Raises:
            QanuniConfigError: If provider construction fails during lazy initialization.
        """
        if self._policies is None:
            self._policies = PolicyTools(self._config, self.get_provider)
        return self._policies

    @property
    def workflow(self) -> WorkflowTools:
        """Access fixed legal orchestration workflows.

        Args:
            None.

        Returns:
            The lazily initialized workflow namespace.

        Raises:
            QanuniConfigError: If provider construction fails during lazy initialization.
        """
        if self._workflow is None:
            self._workflow = WorkflowTools(self)
        return self._workflow

    @property
    def agent(self) -> AgentRuntime:
        """Access the deterministic legal-agent runtime.

        Args:
            None.

        Returns:
            The lazily initialized legal-agent runtime.

        Raises:
            QanuniConfigError: If provider construction fails during lazy initialization.
        """
        if self._agent is None:
            self._agent = AgentRuntime(self)
        return self._agent
