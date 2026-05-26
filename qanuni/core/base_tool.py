"""Base abstractions shared by all tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from time import perf_counter
from typing import Any, ClassVar, Generic, TypeVar, cast

from pydantic import BaseModel, Field, ValidationError, create_model

from qanuni.caching import get_result_cache, should_cache_tool
from qanuni.core.config import QanuniConfig
from qanuni.core.exceptions import (
    ErrorCode,
    QanuniError,
    QanuniOutputError,
    QanuniValidationError,
)
from qanuni.core.prompt_loader import PromptLoader, PromptRender
from qanuni.governance import (
    resolve_legal_reference_asset_hash,
    resolve_logic_asset_hash,
    resolve_prompt_asset_hash,
)
from qanuni.legal_references import LegalReferenceLoader
from qanuni.legal_references.models import LegalReferenceMode, LegalReferenceProfile
from qanuni.models.common import BaseResult, ToolRuntimeConfig
from qanuni.observability import get_observability_recorder, load_pricing_catalog
from qanuni.observability.models import ObservabilityEvent
from qanuni.ontology.adapters import build_ontology_payload
from qanuni.providers.base_provider import BaseProvider, ProviderResponse, ProviderUsage

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseResult)
RESULT_METADATA_FIELD_NAMES: frozenset[str] = frozenset(BaseResult.model_fields)


@dataclass(slots=True)
class _ToolExecutionContext:
    """Store transient execution metadata for one tool call.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    cache_key: str | None = None
    cache_status: str = "bypass"
    usage: ProviderUsage = field(default_factory=ProviderUsage)
    model: str | None = None
    prompt_version: str | None = None
    prompt_asset_hash: str | None = None
    legal_reference_asset_hash: str | None = None
    logic_asset_hash: str | None = None
    estimated_cost_usd: float | None = None


@cache
def build_provider_response_model(output_model: type[BaseResult]) -> type[BaseModel]:
    """Create a provider-facing schema without local metadata-only fields.

    Args:
        output_model: Public SDK result model returned to the caller.

    Returns:
        A Pydantic model containing only the fields the LLM must generate.

    Raises:
        None.
    """
    field_definitions: dict[str, Any] = {}
    field_name: str
    for field_name, model_field in output_model.model_fields.items():
        if field_name in RESULT_METADATA_FIELD_NAMES:
            continue

        default_value: Any
        if model_field.is_required():
            default_value = ...
        elif model_field.default_factory is not None:
            default_value = Field(default_factory=model_field.default_factory)
        else:
            default_value = model_field.default
        field_definitions[field_name] = (model_field.annotation, default_value)

    provider_model: Any = create_model(
        output_model.__name__,
        __module__=output_model.__module__,
        **field_definitions,
    )
    provider_model.__qanuni_output_model__ = output_model
    return cast(type[BaseModel], provider_model)


class BaseTool(ABC, Generic[InputT, OutputT]):
    """Provide shared execution behavior for all SDK tools.

    Args:
        config: Resolved SDK configuration object.
        provider_factory: Zero-argument callable that returns a provider instance.

    Returns:
        None.

    Raises:
        None.
    """

    TOOL_ID: ClassVar[str]
    TIER: ClassVar[str] = "free"
    INPUT_MODEL: ClassVar[type[InputT]]
    OUTPUT_MODEL: ClassVar[type[OutputT]]
    PROMPT_FILE: ClassVar[str | None] = None
    LEGAL_REFERENCE_FILE: ClassVar[str | None] = None

    def __init__(
        self,
        config: QanuniConfig,
        provider_factory: Callable[[], BaseProvider],
    ) -> None:
        """Store shared configuration and the deferred provider factory.

        Args:
            config: Resolved SDK configuration object.
            provider_factory: Zero-argument callable that returns a provider instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._config = config
        self._provider_factory = provider_factory
        self._legal_reference_profile: LegalReferenceProfile | None = None
        self._legal_reference_profile_loaded: bool = False
        self._observability = get_observability_recorder(
            persist=config.observability_persist,
            log_path=config.observability_log_path,
        )
        self._pricing_catalog = load_pricing_catalog(config.model_pricing_file)
        self._result_cache = get_result_cache(
            root_dir=config.cache_dir,
            ttl_seconds=config.cache_ttl_seconds,
        )
        self._logic_asset_hash = resolve_logic_asset_hash(self.__class__)
        self._execution_context = _ToolExecutionContext(logic_asset_hash=self._logic_asset_hash)

    def run(
        self,
        data: InputT | dict[str, Any] | None = None,
        /,
        *,
        runtime: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> OutputT:
        """Validate input, execute the tool, and attach shared result metadata.

        Args:
            data: Optional input model instance or plain dictionary payload.
            runtime: Optional per-call runtime overrides for the provider.
            **kwargs: Keyword arguments used to build the input model when `data` is omitted.

        Returns:
            The finalized structured tool result.

        Raises:
            QanuniValidationError: If the input payload is invalid.
            QanuniConfigError: If provider access is required but not configured.
        """
        started = perf_counter()
        self._reset_execution_context()
        input_data: InputT | None = None
        try:
            self._enforce_access()
            input_data = self._coerce_input(data, kwargs)
            self.validate_input(input_data)

            cached_result = self._load_cached_result(input_data=input_data, runtime=runtime)
            if cached_result is not None:
                elapsed_ms = int((perf_counter() - started) * 1000)
                self._record_success(result=cached_result, elapsed_ms=elapsed_ms)
                return cached_result

            result = self._run(input_data, runtime)
            elapsed_ms = int((perf_counter() - started) * 1000)
            finalized_result = self._finalize(
                input_data=input_data,
                result=result,
                elapsed_ms=elapsed_ms,
            )
            self._store_cached_result(finalized_result)
            self._record_success(result=finalized_result, elapsed_ms=elapsed_ms)
            return finalized_result
        except Exception as exc:
            elapsed_ms = int((perf_counter() - started) * 1000)
            self._record_failure(error=exc, elapsed_ms=elapsed_ms)
            raise

    async def arun(
        self,
        data: InputT | dict[str, Any] | None = None,
        /,
        *,
        runtime: ToolRuntimeConfig | None = None,
        **kwargs: Any,
    ) -> OutputT:
        """Run the tool asynchronously.

        Args:
            data: Optional input model instance or plain dictionary payload.
            runtime: Optional per-call runtime overrides for the provider.
            **kwargs: Keyword arguments used to build the input model when `data` is omitted.

        Returns:
            The finalized structured tool result.

        Raises:
            QanuniValidationError: If the input payload is invalid.
            QanuniConfigError: If provider access is required but not configured.
        """
        started = perf_counter()
        self._reset_execution_context()
        input_data: InputT | None = None
        try:
            self._enforce_access()
            input_data = self._coerce_input(data, kwargs)
            self.validate_input(input_data)

            cached_result = self._load_cached_result(input_data=input_data, runtime=runtime)
            if cached_result is not None:
                elapsed_ms = int((perf_counter() - started) * 1000)
                self._record_success(result=cached_result, elapsed_ms=elapsed_ms)
                return cached_result

            result = await self._arun(input_data, runtime)
            elapsed_ms = int((perf_counter() - started) * 1000)
            finalized_result = self._finalize(
                input_data=input_data,
                result=result,
                elapsed_ms=elapsed_ms,
            )
            self._store_cached_result(finalized_result)
            self._record_success(result=finalized_result, elapsed_ms=elapsed_ms)
            return finalized_result
        except Exception as exc:
            elapsed_ms = int((perf_counter() - started) * 1000)
            self._record_failure(error=exc, elapsed_ms=elapsed_ms)
            raise

    def validate_input(self, input_data: InputT) -> None:
        """Validate business or legal constraints beyond model parsing.

        Args:
            input_data: Parsed input model ready for tool-specific validation.

        Returns:
            None.

        Raises:
            QanuniValidationError: If tool-specific validation fails.
        """

    def _reset_execution_context(self) -> None:
        """Reset transient runtime metadata before a new tool call.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._execution_context = _ToolExecutionContext(logic_asset_hash=self._logic_asset_hash)

    def _cache_allowed(self) -> bool:
        """Return whether the current tool is eligible for selective caching.

        Args:
            None.

        Returns:
            `True` when cache is enabled globally and this tool is allow-listed.

        Raises:
            None.
        """
        return self._config.cache_enabled and should_cache_tool(self.TOOL_ID)

    def _build_cache_key(
        self,
        *,
        input_data: InputT,
        runtime: ToolRuntimeConfig | None,
    ) -> str:
        """Build the selective-cache key for one tool call.

        Args:
            input_data: Parsed tool input for the current call.
            runtime: Optional per-call runtime overrides.

        Returns:
            Stable hexadecimal cache key for the current execution inputs.

        Raises:
            None.
        """
        prompt_version: str | None = None
        prompt_defaults: dict[str, Any] = {}
        if self.PROMPT_FILE is not None:
            prompt_template = PromptLoader.load(self.PROMPT_FILE)
            prompt_version = prompt_template.version
            prompt_defaults = prompt_template.defaults
        merged_runtime = self._merge_runtime(prompt_defaults, runtime)
        legal_reference_profile = self._get_legal_reference_profile()
        material: dict[str, Any] = {
            "tool_id": self.TOOL_ID,
            "input": input_data.model_dump(mode="json"),
            "runtime": merged_runtime.model_dump(mode="json", exclude_none=True),
            "prompt_version": prompt_version,
            "prompt_asset_hash": resolve_prompt_asset_hash(self.PROMPT_FILE),
            "legal_reference_profile_id": (
                legal_reference_profile.profile_id if legal_reference_profile is not None else None
            ),
            "legal_reference_asset_hash": resolve_legal_reference_asset_hash(
                self.LEGAL_REFERENCE_FILE
            ),
            "logic_asset_hash": self._logic_asset_hash,
        }
        return self._result_cache.build_key(material)

    def _load_cached_result(
        self,
        *,
        input_data: InputT,
        runtime: ToolRuntimeConfig | None,
    ) -> OutputT | None:
        """Load a cached finalized result when policy allows it.

        Args:
            input_data: Parsed tool input for the current call.
            runtime: Optional per-call runtime overrides.

        Returns:
            Cached structured result, or `None` when cache should not be used.

        Raises:
            None.
        """
        if not self._cache_allowed():
            self._execution_context.cache_status = "bypass"
            return None
        cache_key = self._build_cache_key(input_data=input_data, runtime=runtime)
        self._execution_context.cache_key = cache_key
        cached_result = self._result_cache.get_model(
            cache_key=cache_key,
            scope_type="tool",
            scope_id=self.TOOL_ID,
            model=self.OUTPUT_MODEL,
        )
        if cached_result is None:
            self._execution_context.cache_status = "miss"
            return None
        self._execution_context.cache_status = "hit"
        return cast(
            OutputT,
            cached_result.model_copy(
                update={
                    "cache_hit": True,
                    "cache_key": cache_key,
                }
            ),
        )

    def _store_cached_result(self, result: OutputT) -> None:
        """Persist a finalized result when caching was enabled for the call.

        Args:
            result: Finalized tool result ready to be cached.

        Returns:
            None.

        Raises:
            None.
        """
        if self._execution_context.cache_status != "miss":
            return
        if self._execution_context.cache_key is None:
            return
        self._result_cache.set_model(
            cache_key=self._execution_context.cache_key,
            scope_type="tool",
            scope_id=self.TOOL_ID,
            value=result,
        )

    def _record_success(self, *, result: OutputT, elapsed_ms: int) -> None:
        """Emit one success event to the observability recorder.

        Args:
            result: Finalized tool result returned to the caller.
            elapsed_ms: End-to-end execution latency in milliseconds.

        Returns:
            None.

        Raises:
            None.
        """
        self._observability.record(
            ObservabilityEvent(
                scope_type="tool",
                scope_id=self.TOOL_ID,
                status="success",
                model=result.model_used,
                latency_ms=elapsed_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                total_tokens=result.tokens_used,
                estimated_cost_usd=result.estimated_cost_usd,
                cache_status=cast(Any, self._execution_context.cache_status),
                prompt_version=result.prompt_version,
                prompt_asset_hash=result.prompt_asset_hash,
                legal_reference_profile_id=result.legal_reference_profile_id,
                legal_reference_asset_hash=result.legal_reference_asset_hash,
                logic_asset_hash=result.logic_asset_hash,
            )
        )

    def _record_failure(self, *, error: Exception, elapsed_ms: int) -> None:
        """Emit one failure event to the observability recorder.

        Args:
            error: Exception raised during tool execution.
            elapsed_ms: End-to-end execution latency in milliseconds.

        Returns:
            None.

        Raises:
            None.
        """
        error_code = error.error_code.value if isinstance(error, QanuniError) else None
        details: dict[str, Any] = (
            error.details
            if isinstance(error, QanuniError)
            else {"exception_type": error.__class__.__name__}
        )
        legal_reference_profile_id: str | None = None
        try:
            legal_reference_profile = self._get_legal_reference_profile()
            if legal_reference_profile is not None:
                legal_reference_profile_id = legal_reference_profile.profile_id
        except QanuniValidationError:
            legal_reference_profile_id = None
        self._observability.record(
            ObservabilityEvent(
                scope_type="tool",
                scope_id=self.TOOL_ID,
                status="failure",
                model=self._execution_context.model,
                latency_ms=elapsed_ms,
                input_tokens=self._execution_context.usage.input_tokens,
                output_tokens=self._execution_context.usage.output_tokens,
                total_tokens=self._execution_context.usage.total_tokens,
                estimated_cost_usd=self._execution_context.estimated_cost_usd,
                cache_status=cast(Any, self._execution_context.cache_status),
                error_code=error_code,
                failure_mode=error.__class__.__name__,
                prompt_version=self._execution_context.prompt_version,
                prompt_asset_hash=self._execution_context.prompt_asset_hash,
                legal_reference_profile_id=legal_reference_profile_id,
                legal_reference_asset_hash=self._execution_context.legal_reference_asset_hash,
                logic_asset_hash=self._execution_context.logic_asset_hash,
                details=details,
            )
        )

    def _coerce_input(
        self,
        data: InputT | dict[str, Any] | None,
        kwargs: dict[str, Any],
    ) -> InputT:
        """Normalize positional model/dict input and keyword input into the tool model.

        Args:
            data: Optional input model instance or plain dictionary payload.
            kwargs: Keyword arguments supplied directly to the tool method.

        Returns:
            A validated input model instance for the tool.

        Raises:
            QanuniValidationError: If mutually exclusive input styles are mixed or unsupported.
        """
        if data is not None and kwargs:
            raise QanuniValidationError(
                "Pass either an input model/dict or keyword arguments, not both.",
                error_code=ErrorCode.VALIDATION_INPUT_CONFLICT,
                details={"tool_id": self.TOOL_ID},
            )
        if isinstance(data, self.INPUT_MODEL):
            return data
        if data is None:
            payload: dict[str, Any] = kwargs
        elif isinstance(data, dict):
            payload = data
        else:
            raise QanuniValidationError(
                f"Expected {self.INPUT_MODEL.__name__} or dict input for {self.TOOL_ID}.",
                error_code=ErrorCode.VALIDATION_INPUT_TYPE,
                details={"tool_id": self.TOOL_ID, "input_model": self.INPUT_MODEL.__name__},
            )
        try:
            return self.INPUT_MODEL.model_validate(payload)
        except ValidationError as exc:
            error_code: ErrorCode = ErrorCode.VALIDATION_FAILED
            error_messages: list[str] = [
                str(error.get("msg", ""))
                for error in exc.errors(include_url=False)
            ]
            if any(
                message.endswith("Provide either contract_text or contract_file.")
                or message.endswith("Provide either document_text or document_file.")
                for message in error_messages
            ):
                error_code = ErrorCode.VALIDATION_DOCUMENT_SOURCE_MISSING
            raise QanuniValidationError(
                "The supplied tool input is invalid.",
                error_code=error_code,
                details={
                    "tool_id": self.TOOL_ID,
                    "input_model": self.INPUT_MODEL.__name__,
                    "errors": exc.errors(include_url=False),
                },
            ) from exc

    def _enforce_access(self) -> None:
        """Retain a compatibility hook for future access policies.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        return None

    def _require_provider(self) -> BaseProvider:
        """Return the configured provider or fail loudly if provider setup fails.

        Args:
            None.

        Returns:
            A configured provider instance.

        Raises:
            QanuniConfigError: If the configured provider cannot be created.
        """
        return self._provider_factory()

    def _load_prompt(self) -> PromptRender:
        """Load a prompt without any user context.

        Args:
            None.

        Returns:
            A rendered prompt object with empty context.

        Raises:
            QanuniValidationError: If the tool does not declare a prompt file.
        """
        if self.PROMPT_FILE is None:
            raise QanuniValidationError(
                f"Tool '{self.TOOL_ID}' does not define a prompt file.",
                error_code=ErrorCode.PROMPT_FILE_MISSING,
                details={"tool_id": self.TOOL_ID},
            )
        return self._render_prompt({})

    def _build_prompt(self, context: dict[str, Any]) -> PromptRender:
        """Render the tool prompt with runtime input context.

        Args:
            context: Template variables used to render the configured prompt file.

        Returns:
            A rendered prompt object ready for provider submission.

        Raises:
            QanuniValidationError: If the tool does not declare a prompt file.
        """
        if self.PROMPT_FILE is None:
            raise QanuniValidationError(
                f"Tool '{self.TOOL_ID}' does not define a prompt file.",
                error_code=ErrorCode.PROMPT_FILE_MISSING,
                details={"tool_id": self.TOOL_ID},
            )
        return self._render_prompt(context)

    def _render_prompt(self, context: dict[str, Any]) -> PromptRender:
        """Render the configured prompt and enforce legal-reference consistency.

        Args:
            context: Template variables used to render the configured prompt file.

        Returns:
            A rendered prompt object ready for provider submission.

        Raises:
            QanuniValidationError: If strict legal-reference prompt metadata is misconfigured.
        """
        if self.PROMPT_FILE is None:
            raise QanuniValidationError(
                f"Tool '{self.TOOL_ID}' does not define a prompt file.",
                error_code=ErrorCode.PROMPT_FILE_MISSING,
                details={"tool_id": self.TOOL_ID},
            )

        prompt_template = PromptLoader.load(self.PROMPT_FILE)
        legal_reference_profile = self._get_legal_reference_profile()
        if (
            prompt_template.legal_reference_mode != LegalReferenceMode.DISABLED
            and legal_reference_profile is None
        ):
            raise QanuniValidationError(
                f"Tool '{self.TOOL_ID}' requires a legal reference profile.",
                error_code=ErrorCode.LEGAL_REFERENCE_REQUIRED,
                details={
                    "tool_id": self.TOOL_ID,
                    "prompt_file": self.PROMPT_FILE,
                    "legal_reference_mode": prompt_template.legal_reference_mode.value,
                },
            )

        return prompt_template.render(
            context,
            legal_reference_profile=legal_reference_profile,
        )

    def _build_prompt_context(self, input_data: InputT) -> dict[str, Any]:
        """Build the final prompt-rendering context from input data and legal references.

        Args:
            input_data: Parsed input model instance for the current call.

        Returns:
            A render context containing input fields and optional legal-reference metadata.

        Raises:
            QanuniValidationError: If the configured legal-reference file is invalid or missing.
        """
        context: dict[str, Any] = input_data.model_dump(mode="json")
        legal_reference_profile: LegalReferenceProfile | None = self._get_legal_reference_profile()
        if legal_reference_profile is None:
            return context

        context.update(
            {
                "legal_reference_profile_id": legal_reference_profile.profile_id,
                "legal_reference_mode": legal_reference_profile.mode.value,
                "legal_reference_source_ids": list(legal_reference_profile.source_ids()),
                "legal_reference_rule_ids": list(legal_reference_profile.rule_ids()),
                "legal_reference_mandatory_rule_ids": list(
                    legal_reference_profile.mandatory_rule_ids()
                ),
                "legal_reference_system_block": legal_reference_profile.render_system_block(),
                "legal_reference_user_block": legal_reference_profile.render_user_block(),
            }
        )
        return context

    def _merge_runtime(
        self,
        prompt_defaults: dict[str, Any],
        runtime: ToolRuntimeConfig | None,
    ) -> ToolRuntimeConfig:
        """Merge global config, prompt defaults, tool overrides, and per-call overrides.

        Args:
            prompt_defaults: Provider defaults defined in the prompt file.
            runtime: Optional per-call runtime overrides.

        Returns:
            A merged runtime configuration object for provider execution.

        Raises:
            None.
        """
        override = self._config.tool_overrides.get(self.TOOL_ID, ToolRuntimeConfig())
        prompt_max_output_tokens: int | None = prompt_defaults.get("max_output_tokens")
        merged = ToolRuntimeConfig(
            model=(
                runtime.model
                if runtime and runtime.model is not None
                else override.model
                if override.model is not None
                else self._config.model
                or prompt_defaults.get("model")
            ),
            timeout_seconds=(
                runtime.timeout_seconds
                if runtime and runtime.timeout_seconds is not None
                else override.timeout_seconds
                if override.timeout_seconds is not None
                else self._config.timeout
            ),
            api_retries=(
                runtime.api_retries
                if runtime and runtime.api_retries is not None
                else override.api_retries
                if override.api_retries is not None
                else self._config.max_retries
            ),
            max_output_tokens=(
                runtime.max_output_tokens
                if runtime and runtime.max_output_tokens is not None
                else override.max_output_tokens
                if override.max_output_tokens is not None
                else max(
                    self._config.max_output_tokens,
                    prompt_max_output_tokens,
                )
                if (
                    self._config.max_output_tokens is not None
                    and prompt_max_output_tokens is not None
                )
                else self._config.max_output_tokens
                if self._config.max_output_tokens is not None
                else prompt_max_output_tokens
            ),
            temperature=(
                runtime.temperature
                if runtime and runtime.temperature is not None
                else override.temperature
                if override.temperature is not None
                else self._config.temperature
                if self._config.temperature is not None
                else prompt_defaults.get("temperature")
            ),
            reasoning_effort=(
                runtime.reasoning_effort
                if runtime and runtime.reasoning_effort is not None
                else override.reasoning_effort
                if override.reasoning_effort is not None
                else prompt_defaults.get("reasoning_effort")
                if prompt_defaults.get("reasoning_effort") is not None
                else self._config.reasoning_effort
            ),
            verbosity=(
                runtime.verbosity
                if runtime and runtime.verbosity is not None
                else override.verbosity
                if override.verbosity is not None
                else prompt_defaults.get("verbosity")
                if prompt_defaults.get("verbosity") is not None
                else self._config.verbosity
            ),
        )
        return merged

    def _call_structured_model(
        self,
        input_data: InputT,
        *,
        runtime: ToolRuntimeConfig | None,
    ) -> ProviderResponse[OutputT]:
        """Render the prompt and call the provider synchronously.

        Args:
            input_data: Parsed input model instance.
            runtime: Optional per-call runtime overrides.

        Returns:
            The provider response containing structured tool output.

        Raises:
            QanuniConfigError: If provider access is unavailable.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider cannot produce valid structured output.
        """
        prompt = self._build_prompt(self._build_prompt_context(input_data))
        provider = self._require_provider()
        runtime_config = self._merge_runtime(prompt.defaults, runtime)
        provider_model: type[BaseModel] = build_provider_response_model(self.OUTPUT_MODEL)
        response = provider.generate_structured(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            response_model=provider_model,
            runtime=runtime_config,
        )
        self._execution_context.model = response.model
        self._execution_context.usage = response.usage
        self._execution_context.prompt_version = prompt.version
        self._execution_context.prompt_asset_hash = resolve_prompt_asset_hash(self.PROMPT_FILE)
        self._execution_context.legal_reference_asset_hash = resolve_legal_reference_asset_hash(
            self.LEGAL_REFERENCE_FILE
        )
        self._execution_context.estimated_cost_usd = self._pricing_catalog.estimate_cost(
            response.model,
            response.usage,
        )
        return ProviderResponse(
            data=self._coerce_provider_output(response.data),
            model=response.model,
            usage=response.usage,
            raw_text=response.raw_text,
        )

    async def _acall_structured_model(
        self,
        input_data: InputT,
        *,
        runtime: ToolRuntimeConfig | None,
    ) -> ProviderResponse[OutputT]:
        """Render the prompt and call the provider asynchronously.

        Args:
            input_data: Parsed input model instance.
            runtime: Optional per-call runtime overrides.

        Returns:
            The provider response containing structured tool output.

        Raises:
            QanuniConfigError: If provider access is unavailable.
            QanuniAPIError: If the provider request fails.
            QanuniOutputError: If the provider cannot produce valid structured output.
        """
        prompt = self._build_prompt(self._build_prompt_context(input_data))
        provider = self._require_provider()
        runtime_config = self._merge_runtime(prompt.defaults, runtime)
        provider_model: type[BaseModel] = build_provider_response_model(self.OUTPUT_MODEL)
        response = await provider.agenerate_structured(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            response_model=provider_model,
            runtime=runtime_config,
        )
        self._execution_context.model = response.model
        self._execution_context.usage = response.usage
        self._execution_context.prompt_version = prompt.version
        self._execution_context.prompt_asset_hash = resolve_prompt_asset_hash(self.PROMPT_FILE)
        self._execution_context.legal_reference_asset_hash = resolve_legal_reference_asset_hash(
            self.LEGAL_REFERENCE_FILE
        )
        self._execution_context.estimated_cost_usd = self._pricing_catalog.estimate_cost(
            response.model,
            response.usage,
        )
        return ProviderResponse(
            data=self._coerce_provider_output(response.data),
            model=response.model,
            usage=response.usage,
            raw_text=response.raw_text,
        )

    def _coerce_provider_output(self, data: BaseModel) -> OutputT:
        """Convert provider-facing payloads into the public SDK result model.

        Args:
            data: Structured payload returned by the provider-facing schema.

        Returns:
            A validated public SDK result model instance.

        Raises:
            QanuniOutputError: If provider output cannot satisfy the public schema.
        """
        if isinstance(data, self.OUTPUT_MODEL):
            return data
        payload: dict[str, Any] = data.model_dump(mode="json")
        try:
            return self.OUTPUT_MODEL.model_validate(payload)
        except ValidationError as exc:
            raise QanuniOutputError(
                "Provider output did not satisfy the public SDK result schema.",
                error_code=ErrorCode.OUTPUT_SCHEMA_MISMATCH,
                details={
                    "tool_id": self.TOOL_ID,
                    "response_model": self.OUTPUT_MODEL.__name__,
                    "errors": exc.errors(include_url=False),
                },
            ) from exc

    def _finalize(
        self,
        *,
        input_data: InputT,
        result: OutputT,
        elapsed_ms: int,
    ) -> OutputT:
        """Attach standardized result metadata before returning the tool output.

        Args:
            input_data: Parsed input model used to produce the result.
            result: Raw structured tool result produced by the implementation.
            elapsed_ms: Execution duration in milliseconds.

        Returns:
            The structured result with standard metadata fields populated.

        Raises:
            None.
        """
        legal_reference_profile: LegalReferenceProfile | None = self._get_legal_reference_profile()
        ontology_payload = build_ontology_payload(
            tool_id=self.TOOL_ID,
            input_data=input_data,
            result=result,
            legal_reference_profile=legal_reference_profile,
        )
        return result.model_copy(
            update={
                "tool_id": self.TOOL_ID,
                "execution_time_ms": elapsed_ms,
                "tokens_used": (
                    result.tokens_used
                    if result.tokens_used is not None
                    else self._execution_context.usage.total_tokens
                ),
                "input_tokens": (
                    result.input_tokens
                    if result.input_tokens is not None
                    else self._execution_context.usage.input_tokens
                ),
                "output_tokens": (
                    result.output_tokens
                    if result.output_tokens is not None
                    else self._execution_context.usage.output_tokens
                ),
                "estimated_cost_usd": (
                    result.estimated_cost_usd
                    if result.estimated_cost_usd is not None
                    else self._execution_context.estimated_cost_usd
                ),
                "model_used": result.model_used or self._execution_context.model or "deterministic",
                "timestamp": datetime.now(UTC),
                "cache_hit": result.cache_hit or self._execution_context.cache_status == "hit",
                "cache_key": result.cache_key or self._execution_context.cache_key,
                "prompt_version": result.prompt_version or self._execution_context.prompt_version,
                "prompt_asset_hash": (
                    result.prompt_asset_hash or self._execution_context.prompt_asset_hash
                ),
                "legal_reference_asset_hash": (
                    result.legal_reference_asset_hash
                    or self._execution_context.legal_reference_asset_hash
                ),
                "logic_asset_hash": (
                    result.logic_asset_hash or self._execution_context.logic_asset_hash
                ),
                "legal_reference_profile_id": (
                    legal_reference_profile.profile_id
                    if legal_reference_profile is not None
                    else None
                ),
                "legal_reference_source_ids": (
                    list(legal_reference_profile.source_ids())
                    if legal_reference_profile is not None
                    else []
                ),
                "legal_reference_rule_ids": (
                    list(legal_reference_profile.rule_ids())
                    if legal_reference_profile is not None
                    else []
                ),
                **ontology_payload,
            }
        )

    def _get_legal_reference_profile(self) -> LegalReferenceProfile | None:
        """Load and cache the tool-specific legal-reference profile when configured.

        Args:
            None.

        Returns:
            The configured legal-reference profile, or `None` when the tool has no packet.

        Raises:
            QanuniValidationError: If the configured legal-reference file is invalid or missing.
        """
        if self._legal_reference_profile_loaded:
            return self._legal_reference_profile

        if self.LEGAL_REFERENCE_FILE is None:
            self._legal_reference_profile_loaded = True
            self._legal_reference_profile = None
            return None

        self._legal_reference_profile = LegalReferenceLoader.load(
            self.LEGAL_REFERENCE_FILE,
            external_catalog_dir=self._config.legal_reference_catalog_dir,
        )
        if self._legal_reference_profile.tool_ids and self.TOOL_ID not in set(
            self._legal_reference_profile.tool_ids
        ):
            raise QanuniValidationError(
                (
                    "Legal reference profile "
                    f"'{self._legal_reference_profile.profile_id}' does not apply "
                    f"to '{self.TOOL_ID}'."
                ),
                error_code=ErrorCode.LEGAL_REFERENCE_INVALID,
                details={
                    "tool_id": self.TOOL_ID,
                    "profile_id": self._legal_reference_profile.profile_id,
                    "allowed_tool_ids": list(self._legal_reference_profile.tool_ids),
                },
            )
        self._legal_reference_profile_loaded = True
        return self._legal_reference_profile

    @abstractmethod
    def _run(self, input_data: InputT, runtime: ToolRuntimeConfig | None) -> OutputT:
        """Execute the tool synchronously.

        Args:
            input_data: Parsed input model instance.
            runtime: Optional per-call runtime overrides.

        Returns:
            The structured tool result.

        Raises:
            QanuniError: If tool execution fails.
        """

    async def _arun(self, input_data: InputT, runtime: ToolRuntimeConfig | None) -> OutputT:
        """Raise unless subclasses implement async execution explicitly.

        Args:
            input_data: Parsed input model instance.
            runtime: Optional per-call runtime overrides.

        Returns:
            The structured tool result.

        Raises:
            QanuniError: If the tool does not implement async execution.
        """
        raise QanuniError(
            f"Tool '{self.TOOL_ID}' does not implement async execution.",
            error_code=ErrorCode.FEATURE_NOT_READY,
            details={"tool_id": self.TOOL_ID, "feature": "async_execution"},
        )
