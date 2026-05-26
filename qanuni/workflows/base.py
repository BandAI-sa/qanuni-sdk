"""Base abstractions for multi-step Qanuni workflows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from pydantic import BaseModel, ValidationError

from qanuni.caching import should_cache_workflow
from qanuni.core.exceptions import ErrorCode, QanuniError, QanuniValidationError
from qanuni.governance import load_packaged_asset_manifest, resolve_logic_asset_hash
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.workflows import WorkflowExecutionOptions, WorkflowState
from qanuni.observability.models import ObservabilityEvent

if TYPE_CHECKING:
    from qanuni.client import LegalClient

InputT = TypeVar("InputT", bound=WorkflowExecutionOptions)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseWorkflow(ABC, Generic[InputT, OutputT]):
    """Provide shared input coercion and runtime-selection behavior for workflows.

    Args:
        client: Shared SDK client used to orchestrate namespace tools.

    Returns:
        None.

    Raises:
        None.
    """

    WORKFLOW_ID: ClassVar[str]
    INPUT_MODEL: ClassVar[type[InputT]]
    OUTPUT_MODEL: ClassVar[type[OutputT]]
    _SAFE_ANALYTIC_RUNTIME_FLOORS: ClassVar[dict[str, int]] = {
        "legal.classify_document_type": 900,
        "legal.extract_clauses": 1800,
        "legal.extract_parties": 1400,
        "legal.extract_dates": 1400,
        "legal.extract_amounts": 1400,
        "legal.extract_obligations": 1800,
        "legal.extract_termination_terms": 1400,
        "legal.extract_dispute_resolution": 1400,
        "drafting.extract_clauses": 1800,
        "drafting.improve": 2600,
        "contracts.gap_analysis": 1800,
        "contracts.risk_score": 1400,
        "compliance.pdpl_check": 1800,
        "compliance.vat_check": 1400,
    }

    def __init__(self, client: LegalClient) -> None:
        """Store the shared SDK client used by the workflow.

        Args:
            client: Shared SDK client used to orchestrate namespace tools.

        Returns:
            None.

        Raises:
            None.
        """
        self._client = client
        self._logic_asset_hash = resolve_logic_asset_hash(self.__class__)

    def run(
        self,
        data: InputT | dict[str, Any] | None = None,
        /,
        **kwargs: Any,
    ) -> OutputT:
        """Validate input and execute the workflow synchronously.

        Args:
            data: Optional workflow input model instance or plain dictionary payload.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            The structured workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        started = perf_counter()
        input_data: InputT | None = None
        cache_key: str | None = None
        try:
            input_data = self._coerce_input(data, kwargs)
            cache_key = self._build_cache_key(input_data) if self._cache_allowed() else None
            cached_output = self._load_cached_result(input_data=input_data, cache_key=cache_key)
            if cached_output is not None:
                elapsed_ms = int((perf_counter() - started) * 1000)
                finalized_cached_output = self._finalize_output(
                    output=cached_output,
                    elapsed_ms=elapsed_ms,
                    cache_hit=True,
                    cache_key=cache_key,
                )
                self._record_success(output=finalized_cached_output, elapsed_ms=elapsed_ms)
                return finalized_cached_output

            output = self._run(input_data)
            elapsed_ms = int((perf_counter() - started) * 1000)
            finalized_output = self._finalize_output(
                output=output,
                elapsed_ms=elapsed_ms,
                cache_hit=False,
                cache_key=cache_key,
            )
            self._store_cached_result(
                input_data=input_data,
                output=finalized_output,
                cache_key=cache_key,
            )
            self._record_success(output=finalized_output, elapsed_ms=elapsed_ms)
            return finalized_output
        except Exception as exc:
            elapsed_ms = int((perf_counter() - started) * 1000)
            self._record_failure(error=exc, elapsed_ms=elapsed_ms)
            raise

    async def arun(
        self,
        data: InputT | dict[str, Any] | None = None,
        /,
        **kwargs: Any,
    ) -> OutputT:
        """Validate input and execute the workflow asynchronously.

        Args:
            data: Optional workflow input model instance or plain dictionary payload.
            **kwargs: Keyword input used when `data` is omitted.

        Returns:
            The structured workflow result.

        Raises:
            QanuniValidationError: If the supplied workflow input is invalid.
        """
        started = perf_counter()
        input_data: InputT | None = None
        cache_key: str | None = None
        try:
            input_data = self._coerce_input(data, kwargs)
            cache_key = self._build_cache_key(input_data) if self._cache_allowed() else None
            cached_output = self._load_cached_result(input_data=input_data, cache_key=cache_key)
            if cached_output is not None:
                elapsed_ms = int((perf_counter() - started) * 1000)
                finalized_cached_output = self._finalize_output(
                    output=cached_output,
                    elapsed_ms=elapsed_ms,
                    cache_hit=True,
                    cache_key=cache_key,
                )
                self._record_success(output=finalized_cached_output, elapsed_ms=elapsed_ms)
                return finalized_cached_output

            output = await self._arun(input_data)
            elapsed_ms = int((perf_counter() - started) * 1000)
            finalized_output = self._finalize_output(
                output=output,
                elapsed_ms=elapsed_ms,
                cache_hit=False,
                cache_key=cache_key,
            )
            self._store_cached_result(
                input_data=input_data,
                output=finalized_output,
                cache_key=cache_key,
            )
            self._record_success(output=finalized_output, elapsed_ms=elapsed_ms)
            return finalized_output
        except Exception as exc:
            elapsed_ms = int((perf_counter() - started) * 1000)
            self._record_failure(error=exc, elapsed_ms=elapsed_ms)
            raise

    def _coerce_input(
        self,
        data: InputT | dict[str, Any] | None,
        kwargs: dict[str, Any],
    ) -> InputT:
        """Normalize model, dictionary, or keyword input into the workflow schema.

        Args:
            data: Optional workflow input model instance or plain dictionary payload.
            kwargs: Keyword arguments supplied directly to the workflow method.

        Returns:
            A validated workflow input model.

        Raises:
            QanuniValidationError: If the input styles are mixed or validation fails.
        """
        if data is not None and kwargs:
            raise QanuniValidationError(
                "Pass either a workflow input model/dict or keyword arguments, not both.",
                error_code=ErrorCode.VALIDATION_INPUT_CONFLICT,
                details={"workflow_id": self.WORKFLOW_ID},
            )
        if isinstance(data, self.INPUT_MODEL):
            return data
        if data is None:
            payload: dict[str, Any] = kwargs
        elif isinstance(data, dict):
            payload = data
        else:
            raise QanuniValidationError(
                f"Expected {self.INPUT_MODEL.__name__} or dict input for {self.WORKFLOW_ID}.",
                error_code=ErrorCode.VALIDATION_INPUT_TYPE,
                details={
                    "workflow_id": self.WORKFLOW_ID,
                    "input_model": self.INPUT_MODEL.__name__,
                },
            )
        try:
            return self.INPUT_MODEL.model_validate(payload)
        except ValidationError as exc:
            raise QanuniValidationError(
                "The supplied workflow input is invalid.",
                error_code=ErrorCode.VALIDATION_FAILED,
                details={
                    "workflow_id": self.WORKFLOW_ID,
                    "input_model": self.INPUT_MODEL.__name__,
                    "errors": exc.errors(include_url=False),
                },
            ) from exc

    def _runtime_for(
        self,
        input_data: InputT,
        tool_id: str,
    ) -> ToolRuntimeConfig | None:
        """Resolve runtime overrides for a specific tool call inside the workflow.

        Args:
            input_data: Parsed workflow input used for the current execution.
            tool_id: Stable tool identifier about to be called.

        Returns:
            A per-tool runtime override if configured, otherwise the shared runtime.

        Raises:
            None.
        """
        if tool_id in input_data.step_runtime_overrides:
            return input_data.step_runtime_overrides[tool_id]
        return self._apply_internal_runtime_policy(
            shared_runtime=input_data.shared_runtime,
            tool_id=tool_id,
        )

    def _apply_internal_runtime_policy(
        self,
        *,
        shared_runtime: ToolRuntimeConfig | None,
        tool_id: str,
    ) -> ToolRuntimeConfig | None:
        """Stabilize internal structured-analysis calls inside workflows.

        Args:
            shared_runtime: Shared runtime supplied for the workflow execution.
            tool_id: Stable tool identifier about to be called.

        Returns:
            A safe per-tool runtime override, or the original shared runtime when
            no stabilization is needed.

        Raises:
            None.
        """
        min_output_tokens = self._SAFE_ANALYTIC_RUNTIME_FLOORS.get(tool_id)
        if min_output_tokens is None:
            return shared_runtime

        baseline = shared_runtime or ToolRuntimeConfig()
        configured_max_output_tokens = baseline.max_output_tokens or 0
        return baseline.model_copy(
            update={
                "verbosity": "low",
                "reasoning_effort": "low",
                "max_output_tokens": max(configured_max_output_tokens, min_output_tokens),
            }
        )

    def _cache_allowed(self) -> bool:
        """Return whether this workflow is eligible for selective caching.

        Args:
            None.

        Returns:
            `True` when workflow caching is enabled and this workflow is allow-listed.

        Raises:
            None.
        """
        return self._client.config.cache_enabled and should_cache_workflow(self.WORKFLOW_ID)

    def _build_cache_key(self, input_data: InputT) -> str:
        """Build the selective-cache key for one workflow run.

        Args:
            input_data: Parsed workflow input for the current execution.

        Returns:
            Stable hashed cache key for the current workflow execution.

        Raises:
            None.
        """
        material: dict[str, Any] = {
            "workflow_id": self.WORKFLOW_ID,
            "input": input_data.model_dump(mode="json"),
            "asset_manifest_fingerprint": load_packaged_asset_manifest().fingerprint,
            "logic_asset_hash": self._logic_asset_hash,
        }
        return self._client.result_cache.build_key(material)

    def _load_cached_result(self, *, input_data: InputT, cache_key: str | None) -> OutputT | None:
        """Load a cached finalized workflow result when policy allows it.

        Args:
            input_data: Parsed workflow input for the current execution.
            cache_key: Precomputed workflow cache key for the current execution.

        Returns:
            Cached workflow result, or `None` when cache should not be used.

        Raises:
            None.
        """
        if not self._cache_allowed():
            return None
        if cache_key is None:
            return None
        cached_output = self._client.result_cache.get_model(
            cache_key=cache_key,
            scope_type="workflow",
            scope_id=self.WORKFLOW_ID,
            model=self._result_model(),
        )
        if cached_output is None:
            return None
        return cast(OutputT, cached_output)

    def _store_cached_result(
        self,
        *,
        input_data: InputT,
        output: OutputT,
        cache_key: str | None,
    ) -> None:
        """Persist one finalized workflow result when caching is enabled.

        Args:
            input_data: Parsed workflow input for the current execution.
            output: Finalized workflow result to cache.
            cache_key: Optional precomputed workflow cache key for the current execution.

        Returns:
            None.

        Raises:
            None.
        """
        if not self._cache_allowed():
            return
        if cache_key is None:
            cache_key = self._build_cache_key(input_data)
        self._client.result_cache.set_model(
            cache_key=cache_key,
            scope_type="workflow",
            scope_id=self.WORKFLOW_ID,
            value=cast(BaseModel, output),
        )

    def _result_model(self) -> type[BaseModel]:
        """Return the output model class used by the workflow.

        Args:
            None.

        Returns:
            The workflow result model type.

        Raises:
            TypeError: If the generic type cannot be recovered.
        """
        return cast(type[BaseModel], self.OUTPUT_MODEL)

    def _finalize_output(
        self,
        *,
        output: OutputT,
        elapsed_ms: int,
        cache_hit: bool,
        cache_key: str | None,
    ) -> OutputT:
        """Attach aggregated runtime metrics to workflow state.

        Args:
            output: Raw workflow result returned by the workflow implementation.
            elapsed_ms: End-to-end execution latency in milliseconds.
            cache_hit: Whether the workflow result came from cache.
            cache_key: Optional workflow cache key associated with the result.

        Returns:
            Finalized workflow result with enriched shared state.

        Raises:
            None.
        """
        workflow_state = getattr(output, "state", None)
        if not isinstance(workflow_state, WorkflowState):
            return output

        step_payload: dict[str, Any]
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        estimated_cost = 0.0
        has_cost = False
        models_used: list[str] = []
        for step_payload in workflow_state.step_outputs.values():
            if "input_tokens" in step_payload and step_payload["input_tokens"] is not None:
                input_tokens += int(step_payload["input_tokens"])
            if "output_tokens" in step_payload and step_payload["output_tokens"] is not None:
                output_tokens += int(step_payload["output_tokens"])
            if "tokens_used" in step_payload and step_payload["tokens_used"] is not None:
                total_tokens += int(step_payload["tokens_used"])
            if (
                "estimated_cost_usd" in step_payload
                and step_payload["estimated_cost_usd"] is not None
            ):
                estimated_cost += float(step_payload["estimated_cost_usd"])
                has_cost = True
            model_used = step_payload.get("model_used")
            if isinstance(model_used, str) and model_used not in {"", "deterministic"}:
                if model_used not in models_used:
                    models_used.append(model_used)

        finalized_state = workflow_state.model_copy(
            update={
                "execution_time_ms": elapsed_ms,
                "tokens_used": total_tokens or None,
                "input_tokens": input_tokens or None,
                "output_tokens": output_tokens or None,
                "estimated_cost_usd": round(estimated_cost, 8) if has_cost else None,
                "model_used": (
                    models_used[0]
                    if len(models_used) == 1
                    else "mixed"
                    if models_used
                    else "deterministic"
                ),
                "cache_hit": cache_hit,
                "cache_key": cache_key,
                "logic_asset_hash": self._logic_asset_hash,
            }
        )
        return output.model_copy(update={"state": finalized_state})

    def _record_success(self, *, output: OutputT, elapsed_ms: int) -> None:
        """Emit one success workflow event to the observability recorder.

        Args:
            output: Finalized workflow result returned to the caller.
            elapsed_ms: End-to-end execution latency in milliseconds.

        Returns:
            None.

        Raises:
            None.
        """
        workflow_state = getattr(output, "state", None)
        if not isinstance(workflow_state, WorkflowState):
            return
        self._client.observability.record(
            ObservabilityEvent(
                scope_type="workflow",
                scope_id=self.WORKFLOW_ID,
                status="success",
                model=workflow_state.model_used,
                latency_ms=elapsed_ms,
                input_tokens=workflow_state.input_tokens,
                output_tokens=workflow_state.output_tokens,
                total_tokens=workflow_state.tokens_used,
                estimated_cost_usd=workflow_state.estimated_cost_usd,
                cache_status=(
                    "hit"
                    if workflow_state.cache_hit
                    else "miss"
                    if self._cache_allowed()
                    else "bypass"
                ),
                logic_asset_hash=workflow_state.logic_asset_hash,
                details={"step_count": len(workflow_state.steps)},
            )
        )

    def _record_failure(self, *, error: Exception, elapsed_ms: int) -> None:
        """Emit one failure workflow event to the observability recorder.

        Args:
            error: Exception raised during workflow execution.
            elapsed_ms: End-to-end execution latency in milliseconds.

        Returns:
            None.

        Raises:
            None.
        """
        error_code = error.error_code.value if isinstance(error, QanuniError) else None
        self._client.observability.record(
            ObservabilityEvent(
                scope_type="workflow",
                scope_id=self.WORKFLOW_ID,
                status="failure",
                latency_ms=elapsed_ms,
                cache_status="bypass" if not self._cache_allowed() else "miss",
                error_code=error_code,
                failure_mode=error.__class__.__name__,
                logic_asset_hash=self._logic_asset_hash,
            )
        )

    @abstractmethod
    def _run(self, input_data: InputT) -> OutputT:
        """Execute the workflow synchronously.

        Args:
            input_data: Parsed workflow input model.

        Returns:
            The structured workflow result.

        Raises:
            QanuniValidationError: If required workflow context is missing.
        """

    async def _arun(self, input_data: InputT) -> OutputT:
        """Raise unless subclasses implement async execution explicitly.

        Args:
            input_data: Parsed workflow input model.

        Returns:
            The structured workflow result.

        Raises:
            QanuniValidationError: If async execution is not implemented by the workflow.
        """
        raise QanuniValidationError(
            f"Workflow '{self.WORKFLOW_ID}' does not implement async execution.",
            error_code=ErrorCode.FEATURE_NOT_READY,
            details={"workflow_id": self.WORKFLOW_ID, "feature": "async_execution"},
        )
