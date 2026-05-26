# Qanuni SDK

Qanuni is an Arabic-first Python SDK for Saudi-focused legal workflows. This package is the free edition: no activation, no license token, no premium gate, and async access is available in the same build.

Deterministic labor calculators work without OpenAI. Prompt-backed tools, workflows, the agent runtime, and the MCP server need an OpenAI key or a custom provider.

## Install

Base package:

```bash
python -m pip install --upgrade qanuni-sdk
```

Optional extras:

```bash
python -m pip install --upgrade "qanuni-sdk[pdf]"
python -m pip install --upgrade "qanuni-sdk[mcp]"
```

## Quick Start

```python
import os

from qanuni import LegalClient

client = LegalClient(api_key=os.getenv("OPENAI_API_KEY"))

result = client.contracts.risk_score(
    contract_text="The contractor performs the work and payment is made later.",
    contract_type="service_agreement",
)

print(result.risk_level)
print(result.summary)
```

Deterministic labor example:

```python
from qanuni import LegalClient

client = LegalClient()

benefit = client.labor.end_of_service(
    monthly_salary=12000,
    years_of_service=7.5,
    termination_reason="resignation",
    contract_type="indefinite",
)

print(benefit.total_amount)
```

## How Calls Work

All tool methods support:

- keyword arguments
- a plain `dict`
- a typed input model instance

All tool namespaces expose sync and async methods:

- `client.legal.extract_parties(...)`
- `await client.legal.aextract_parties(...)`

Prompt-backed tool methods accept `_config=ToolRuntimeConfig(...)` for per-call runtime overrides. Workflows and the agent runtime use `shared_runtime` and `step_runtime_overrides`.

Document-oriented calls accept direct text or file paths:

- `document_text` or `document_file`
- `contract_text` or `contract_file`
- `support_document_text` or `support_document_file`

PDF file input requires the `pdf` extra.

## Public Surface

### Tool Namespaces

| Namespace | Core methods |
|---|---|
| `client.labor` | `end_of_service`, `probation_check`, `generate_contract` |
| `client.contracts` | `gap_analysis`, `risk_score`, `generate_nda`, `generate_mou` |
| `client.compliance` | `generate_privacy_policy`, `pdpl_check`, `vat_check`, `demand_letter` |
| `client.drafting` | `improve`, `summarize`, `simplify`, `extract_clauses` |
| `client.legal` | `classify_document_type`, `extract_clauses`, `extract_parties`, `extract_dates`, `extract_amounts`, `extract_obligations`, `extract_termination_terms`, `extract_dispute_resolution` |
| `client.policies` | `generate_hr_policy`, `job_description` |

### Workflows

| Workflow | What it does |
|---|---|
| `workflow.contract_review` | classification, extraction, gap analysis, risk scoring, recommendations, optional redlines |
| `workflow.employment_review` | document analysis plus probation and end-of-service branches |
| `workflow.privacy_compliance_review` | PDPL review with optional remediation-draft generation and re-check |
| `workflow.pre_litigation_notice` | optional support analysis plus demand-letter generation and improvement |
| `workflow.policy_generation_review` | branch-based policy or job-description generation plus review |

### Agent Runtime

Public agent methods:

- `client.agent.list_capabilities()`
- `client.agent.plan(...)`
- `client.agent.run(...)`
- `await client.agent.arun(...)`

Supported scenarios:

- `contract_review_only`
- `contract_dispute_notice`
- `employment_rights_review`
- `privacy_remediation`
- `policy_creation_review`

The agent is deterministic: it plans only against approved workflows, stops when required inputs are missing, and returns `completed`, `needs_more_information`, or `blocked`.

### MCP Surface

Install the MCP extra, then serve:

```bash
set QANUNI_MCP_AUTH_TOKEN=change-this-long-random-token
qanuni-mcp-server serve --host 127.0.0.1 --port 8088
```

Curated MCP tools:

- `workflow_contract_review`
- `workflow_pre_litigation_notice`
- `legal_classify_document_type`
- `legal_extract_clauses`
- `legal_extract_parties`
- `legal_extract_dates`
- `legal_extract_amounts`
- `legal_extract_obligations`
- `legal_extract_termination_terms`
- `legal_extract_dispute_resolution`
- `contracts_risk_score`
- `compliance_demand_letter`

Resource URIs:

- `qanuni://references/catalog`
- `qanuni://references/{packet_key}`
- `qanuni://runs`
- `qanuni://runs/{run_id}/output`
- `qanuni://runs/{run_id}/state`
- `qanuni://runs/{run_id}/findings`
- `qanuni://runs/{run_id}/artifacts/{artifact_name}`

## Common Result Metadata

All tool results include their tool-specific payload plus shared metadata such as:

- `tool_id`
- `execution_time_ms`
- `tokens_used`
- `estimated_cost_usd`
- `model_used`
- `cache_hit`
- `prompt_version`
- `legal_references`
- `findings`
- `recommended_actions`

Workflow results additionally expose a normalized `state` object with step outputs, findings, references, timeline items, and generated artifacts.

## Configuration

Important environment variables:

- `OPENAI_API_KEY`
- `QANUNI_MODEL`
- `QANUNI_LANGUAGE`
- `QANUNI_JURISDICTION`
- `QANUNI_TIMEOUT`
- `QANUNI_MAX_RETRIES`
- `QANUNI_MAX_OUTPUT_TOKENS`
- `QANUNI_REASONING_EFFORT`
- `QANUNI_VERBOSITY`
- `QANUNI_CACHE_ENABLED`
- `QANUNI_OBSERVABILITY_PERSIST`
- `QANUNI_MODEL_PRICING_FILE`

You can also load a YAML config with:

```python
from qanuni import LegalClient

client = LegalClient.from_config(".qanuni.yaml")
```

## Caching And Observability

Selective caching is available for mature review-style tools and for these workflows:

- `workflow.contract_review`
- `workflow.employment_review`
- `workflow.privacy_compliance_review`

Generator-style calls such as NDA generation are intentionally not cached.

Use `client.observability.snapshot()` to inspect runtime events and `client.observability.clear()` to reset them.

## Errors

Structured failures inherit from `QanuniError` and expose `error_code` plus `details`.

Common codes include:

- `QANUNI_CONFIG_API_KEY_MISSING`
- `QANUNI_VALIDATION_INPUT_CONFLICT`
- `QANUNI_VALIDATION_DOCUMENT_SOURCE_MISSING`
- `QANUNI_VALIDATION_DOCUMENT_PATH_MISSING`
- `QANUNI_API_PROVIDER_FAILURE`
- `QANUNI_OUTPUT_SCHEMA_MISMATCH`
- `QANUNI_MCP_AUTH_REQUIRED`
- `QANUNI_MCP_RATE_LIMITED`

## Commands And Guides

Useful commands:

```bash
qanuni-examples --list
qanuni-acceptance --list
qanuni-acceptance --mode mocked
qanuni-mcp-smoke --mode mocked
qanuni-governance validate-assets
qanuni-release-check --allow-dirty
```

More repository docs:

- root SDK reference: [README.md](README.md)
- examples guide: [examples/README.md](examples/README.md)
- acceptance guide: [docs/guides/README_ACCEPTANCE.md](docs/guides/README_ACCEPTANCE.md)
- publishing guide: [docs/guides/README_PUBLISHING.md](docs/guides/README_PUBLISHING.md)
