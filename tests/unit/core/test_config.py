from __future__ import annotations

from pathlib import Path

from qanuni import LegalClient
from qanuni.core.config import QanuniConfig


def test_config_defaults() -> None:
    config = QanuniConfig(_env_file=None)
    assert config.model == "gpt-5-mini"
    assert config.language == "ar"
    assert config.timeout == 60
    assert config.max_retries == 0
    assert config.max_output_tokens is None
    assert config.reasoning_effort is None
    assert config.verbosity is None
    assert config.cache_enabled is False
    assert config.cache_ttl_seconds == 86400
    assert config.agent_logging_enabled is True
    assert config.agent_log_dir == Path("logs/agent")
    assert config.asset_manifest_enforced is True


def test_client_from_config_file(tmp_path: Path) -> None:
    config_file = tmp_path / ".qanuni.yaml"
    config_file.write_text(
        """
qanuni:
  legal_reference_catalog_dir: "custom-refs"
  asset_manifest_enforced: false
openai:
  model: gpt-5.4-mini
  temperature: 0.2
locale:
  language: ar
  jurisdiction: SA
performance:
  timeout: 45
  max_retries: 1
  cache_enabled: true
  cache_ttl_seconds: 7200
  model_pricing_file: "pricing.yaml"
logging:
  observability_persist: true
  observability_log_path: ".qanuni_observability/test.jsonl"
  agent_logging_enabled: false
  agent_log_dir: ".qanuni_logs/agent"
tools:
  drafting.improve:
    max_output_tokens: 1234
        """.strip(),
        encoding="utf-8",
    )
    client = LegalClient.from_config(config_file)
    assert client.config.legal_reference_catalog_dir == Path("custom-refs")
    assert client.config.model == "gpt-5.4-mini"
    assert client.config.temperature == 0.2
    assert client.config.timeout == 45
    assert client.config.max_retries == 1
    assert client.config.cache_enabled is True
    assert client.config.cache_ttl_seconds == 7200
    assert client.config.model_pricing_file == Path("pricing.yaml")
    assert client.config.observability_persist is True
    assert client.config.observability_log_path == Path(".qanuni_observability/test.jsonl")
    assert client.config.agent_logging_enabled is False
    assert client.config.agent_log_dir == Path(".qanuni_logs/agent")
    assert client.config.asset_manifest_enforced is False
    assert client.config.tool_overrides["drafting.improve"].max_output_tokens == 1234


def test_api_key_value_returns_secret() -> None:
    config = QanuniConfig(_env_file=None, api_key="sk-demo")
    assert config.api_key_value() == "sk-demo"
