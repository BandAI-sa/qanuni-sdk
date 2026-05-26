# Qanuni SDK Free Edition

Qanuni is an Arabic-first Python SDK for Saudi-focused legal work. This repository packages the free edition: no activation flow, no license token, no seat management, and no premium gate. If you provide an OpenAI API key, prompt-backed tools run immediately. The deterministic labor calculators run without OpenAI.

## What This Package Includes

- 25 callable SDK tools across `labor`, `contracts`, `compliance`, `drafting`, `legal`, and `policies`
- 5 fixed multi-step workflows under `client.workflow`
- 1 deterministic legal agent runtime under `client.agent`
- 1 optional curated MCP server surface for external agentic clients
- Acceptance, governance, release, and example CLIs

## Product Surface At A Glance

| Surface | What it gives you |
|---|---|
| `client.labor` | Deterministic Saudi labor calculations plus Arabic contract generation |
| `client.contracts` | Gap analysis, risk scoring, NDA generation, and MOU generation |
| `client.compliance` | Privacy-policy generation, PDPL checks, VAT checks, and demand letters |
| `client.drafting` | Improvement, summarization, simplification, and clause-structure extraction |
| `client.legal` | Atomic legal extraction primitives for classification, parties, dates, money, obligations, termination, and dispute resolution |
| `client.policies` | HR policy generation and job-description generation |
| `client.workflow` | Orchestrated contract, employment, privacy, notice, and policy-review flows |
| `client.agent` | Deterministic plan-and-execute runtime that selects approved workflows only |
| `qanuni-mcp-server` | Optional MCP server exposing a curated subset of tools and workflows |

## Installation

Base SDK:

```bash
python -m pip install --upgrade qanuni-sdk
```

Add PDF ingestion support:

```bash
python -m pip install --upgrade "qanuni-sdk[pdf]"
```

Add the MCP server surface:

```bash
python -m pip install --upgrade "qanuni-sdk[mcp]"
```

Typical local development install:

```bash
python -m pip install -e .[dev]
```

## Quick Start

Deterministic labor calculation:

```python
from qanuni import LegalClient

client = LegalClient()

result = client.labor.end_of_service(
    monthly_salary=12000,
    years_of_service=7.5,
    termination_reason="resignation",
    contract_type="indefinite",
)

print(result.total_amount)
print(result.legal_explanation)
```

Prompt-backed tool:

```python
import os

from qanuni import LegalClient

client = LegalClient(api_key=os.getenv("OPENAI_API_KEY"))

result = client.contracts.risk_score(
    contract_text="The contractor delivers the services and payment is made later.",
    contract_type="service_agreement",
)

print(result.risk_level)
print(result.mitigation_priorities)
```

Workflow:

```python
workflow_result = client.workflow.contract_review(
    document_file="service_agreement.pdf",
    contract_type="service_agreement",
    include_redlines=True,
)

print(workflow_result.executive_summary)
print(workflow_result.amendment_recommendations)
```

Agent:

```python
agent_result = client.agent.run(
    goal="Review the contract and prepare a pre-litigation demand path.",
    documents=[
        {
            "file_path": "service_agreement.pdf",
            "document_type": "service_agreement",
        }
    ],
    facts={
        "sender_name": "Company A",
        "recipient_name": "Company B",
        "claim_type": "contractual receivables",
        "incident_description": "Payment is overdue.",
        "deadline_days": 7,
        "threat_of_action": "Legal action will follow if payment is not made.",
    },
)

print(agent_result.status)
print(agent_result.answer_text)
```

## Public Client API

```python
from qanuni import LegalClient

client = LegalClient(
    api_key="sk-...",
    model="gpt-5-mini",
    language="ar",
    jurisdiction="SA",
)
```

### `LegalClient(...)`

Constructor arguments are forwarded into `QanuniConfig`. The most important kwargs are:

- `api_key`
- `model`
- `language`
- `jurisdiction`
- `timeout`
- `max_retries`
- `max_output_tokens`
- `temperature`
- `reasoning_effort`
- `verbosity`
- `cache_enabled`
- `cache_dir`
- `cache_ttl_seconds`
- `observability_persist`
- `observability_log_path`
- `agent_logging_enabled`
- `agent_log_dir`
- `asset_manifest_enforced`
- `model_pricing_file`
- `provider_factory`

### `LegalClient.from_config(path)`

Loads YAML and supports both flat keys and nested sections:

- `openai`
- `locale`
- `performance`
- `logging`
- `qanuni`
- `tools`

Example:

```yaml
openai:
  api_key: ${OPENAI_API_KEY}
  model: gpt-5-mini
  max_tokens: 3200
  temperature: 0.2
  reasoning_effort: low
  verbosity: low

locale:
  language: ar
  jurisdiction: SA

performance:
  timeout: 60
  max_retries: 0
  cache_enabled: true
  cache_dir: .qanuni_cache
  cache_ttl_seconds: 86400
  model_pricing_file: pricing.yaml

logging:
  verbose: false
  level: WARNING
  observability_persist: true
  observability_log_path: .qanuni_observability/qanuni_events.jsonl
  agent_logging_enabled: true
  agent_log_dir: logs/agent

qanuni:
  legal_reference_catalog_dir: null
  asset_manifest_enforced: true
```

### Other Public Client Methods And Properties

| Member | Purpose |
|---|---|
| `client.config` | Resolved `QanuniConfig` instance |
| `client.get_provider()` | Returns the lazily created provider instance |
| `client.list_tools(...)` | Returns implemented `ToolMetadata` records; supports `tier`, `namespace`, and `category` filters |
| `client.list_tool_access(...)` | Same catalog shape plus `available` and `reason` |
| `client.pricing_catalog` | Loaded `ModelPricingCatalog` used for cost estimation |
| `client.result_cache` | Shared `ResultCache` instance |
| `client.observability` | Shared `ObservabilityRecorder` |
| `client.labor` / `contracts` / `compliance` / `drafting` / `legal` / `policies` | Tool namespaces |
| `client.workflow` | Workflow namespace |
| `client.agent` | Deterministic legal agent runtime |

## How Calls Work

### Three Supported Invocation Styles

Every tool method accepts exactly one of these patterns:

1. Keyword arguments
2. A plain `dict`
3. A typed input model instance

Examples:

```python
from qanuni.models.common import ToolRuntimeConfig
from qanuni.models.contracts import GapAnalysisInput

client.contracts.gap_analysis(
    contract_text="...",
    contract_type="service_agreement",
)

client.contracts.gap_analysis(
    {
        "contract_text": "...",
        "contract_type": "service_agreement",
    }
)

client.contracts.gap_analysis(
    GapAnalysisInput(
        contract_text="...",
        contract_type="service_agreement",
    ),
    _config=ToolRuntimeConfig(max_output_tokens=1800),
)
```

Do not mix `data` plus kwargs in the same call. That raises `QANUNI_VALIDATION_INPUT_CONFLICT`.

### Sync And Async

Every tool and workflow has an async alias:

- `client.legal.extract_parties(...)`
- `await client.legal.aextract_parties(...)`

The agent runtime also supports:

- `client.agent.plan(...)`
- `client.agent.run(...)`
- `await client.agent.arun(...)`

### Document Inputs

Qanuni supports both direct text and file paths.

- `document_text`, `contract_text`, `support_document_text`: direct inline text
- `document_file`, `contract_file`, `support_document_file`: file paths
- UTF-8 text files work out of the box
- `.pdf` files are supported when the `pdf` extra is installed
- if both text and file are provided, the direct text is used first

### Per-Call Runtime Overrides

Tool methods accept `_config=ToolRuntimeConfig(...)`.

```python
from qanuni.models.common import ToolRuntimeConfig

result = client.compliance.demand_letter(
    sender_name="Company A",
    recipient_name="Company B",
    claim_type="late payment",
    incident_description="Invoice is overdue.",
    deadline_days=7,
    threat_of_action="We will escalate legally.",
    _config=ToolRuntimeConfig(
        model="gpt-5-mini",
        timeout_seconds=90,
        max_output_tokens=2400,
        reasoning_effort="low",
        verbosity="low",
    ),
)
```

Workflow and agent surfaces use:

- `shared_runtime`
- `step_runtime_overrides`

Important behavior:

- prompt defaults can override broad global reasoning and verbosity settings
- workflows intentionally clamp some analytic steps to low verbosity and low reasoning effort
- generator-style steps keep the runtime you requested unless a prompt default overrides it

### Shared Result Metadata

All tool results include the tool-specific fields shown below plus the common metadata from `BaseResult`:

- `tool_id`
- `execution_time_ms`
- `tokens_used`
- `input_tokens`
- `output_tokens`
- `estimated_cost_usd`
- `model_used`
- `timestamp`
- `cache_hit`
- `cache_key`
- `prompt_version`
- `prompt_asset_hash`
- `legal_reference_asset_hash`
- `logic_asset_hash`
- `confidence_score`
- `legal_reference_profile_id`
- `legal_reference_source_ids`
- `legal_reference_rule_ids`
- `legal_references`
- `evidence_items`
- `findings`
- `recommended_actions`
- `affected_parties`
- `timeline_events`

## Configuration Reference

### Core SDK Environment Variables

| Variable | Default | Meaning |
|---|---|---|
| `OPENAI_API_KEY` | unset | OpenAI key for prompt-backed tools |
| `QANUNI_LEGAL_REFERENCE_CATALOG_DIR` | unset | External legal-reference catalog override |
| `QANUNI_MODEL` | `gpt-5-mini` | Default provider model |
| `QANUNI_LANGUAGE` | `ar` | Default language |
| `QANUNI_JURISDICTION` | `SA` | Default jurisdiction |
| `QANUNI_TIMEOUT` | `60` | Request timeout in seconds |
| `QANUNI_MAX_RETRIES` | `0` | Provider retries above the first attempt |
| `QANUNI_MAX_OUTPUT_TOKENS` | unset | Global output ceiling |
| `QANUNI_TEMPERATURE` | unset | Global temperature |
| `QANUNI_REASONING_EFFORT` | unset | Global reasoning effort |
| `QANUNI_VERBOSITY` | unset | Global verbosity |
| `QANUNI_VERBOSE` | `false` | Verbose SDK logging flag |
| `QANUNI_LOG_LEVEL` | `WARNING` | Log level |
| `QANUNI_CACHE_ENABLED` | `false` | Enables selective caching |
| `QANUNI_CACHE_DIR` | `.qanuni_cache` | Cache directory |
| `QANUNI_CACHE_TTL_SECONDS` | `86400` | Cache TTL |
| `QANUNI_OBSERVABILITY_PERSIST` | `false` | Persist observability JSONL |
| `QANUNI_OBSERVABILITY_LOG_PATH` | `.qanuni_observability/qanuni_events.jsonl` | Observability log file |
| `QANUNI_AGENT_LOGGING_ENABLED` | `true` | Persist per-run agent logs |
| `QANUNI_AGENT_LOG_DIR` | `logs/agent` | Agent log directory |
| `QANUNI_ASSET_MANIFEST_ENFORCED` | `true` | Validate governed assets at startup |
| `QANUNI_MODEL_PRICING_FILE` | unset | Custom pricing catalog override |

### MCP Environment Variables

| Variable | Default | Meaning |
|---|---|---|
| `QANUNI_MCP_HOST` | `127.0.0.1` | Bind host |
| `QANUNI_MCP_PORT` | `8088` | Bind port |
| `QANUNI_MCP_MOUNT_PATH` | `/mcp` | MCP mount path |
| `QANUNI_MCP_AUTH_TOKEN` | unset | Bearer token used when auth is enabled |
| `QANUNI_MCP_REQUIRE_AUTH` | `true` | Require bearer auth for MCP routes |
| `QANUNI_MCP_HEALTHCHECK_OPEN` | `true` | Keep `/healthz` open even when auth is required |
| `QANUNI_MCP_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window |
| `QANUNI_MCP_RATE_LIMIT_MAX_REQUESTS` | `60` | Max requests per window |
| `QANUNI_MCP_AUDIT_LOG_PATH` | `.qanuni_audit/qanuni_mcp_audit.jsonl` | MCP audit log |

## Namespace Reference

### `client.labor`

Deterministic and labor-specific use cases:

- calculate end-of-service awards for resignation, employer termination, contract completion, or mutual agreement
- validate probation periods with or without written extensions
- generate a first-pass Arabic employment contract draft with configurable benefits and work rules

| Method | Async | Required inputs | Optional inputs | Returns |
|---|---|---|---|---|
| `labor.end_of_service` | `labor.aend_of_service` | `monthly_salary`, `years_of_service`, `termination_reason`, `contract_type` | - | `total_amount`, `calculation_breakdown`, `legal_explanation`, `applicable_articles`, `additional_entitlements` |
| `labor.probation_check` | `labor.aprobation_check` | `probation_duration_days` | `contract_type`, `written_extension`, `contract_text_snippet` | `is_legal`, `max_allowed_days`, `violations`, `employee_rights_during_probation`, `employer_rights_during_probation`, `legal_explanation` |
| `labor.generate_contract` | `labor.agenerate_contract` | `employer_name`, `employee_name`, `job_title`, `monthly_salary`, `contract_type`, `work_location` | `probation_days`, `working_hours_per_week`, `annual_leave_days`, `benefits` | `contract_text`, `included_clauses`, `compliance_notes`, `configurable_points` |

Notes:

- `labor.end_of_service` and `labor.probation_check` are deterministic and do not need OpenAI
- `labor.probation_check` accepts both `probation_duration_days` and the alias `probation_days`
- `labor.probation_check` also accepts both `written_extension` and the alias `extension_in_writing`
- `labor.generate_contract` is prompt-backed and needs an API key or custom provider

### `client.contracts`

Contract use cases:

- analyze a signed or draft agreement for missing protections
- convert contract quality into a risk score and mitigation priorities
- draft NDAs and MOUs in Arabic for Saudi-oriented commercial use

| Method | Async | Required inputs | Optional inputs | Returns |
|---|---|---|---|---|
| `contracts.gap_analysis` | `contracts.agap_analysis` | `contract_type` | `contract_text`, `contract_file` | `gaps`, `overall_risk_level`, `missing_mandatory_clauses`, `ambiguous_clauses`, `compliance_score`, `summary` |
| `contracts.risk_score` | `contracts.arisk_score` | - | `contract_text`, `contract_file`, `contract_type` | `risk_score`, `risk_level`, `primary_risk_drivers`, `missing_safeguards`, `mitigation_priorities`, `summary` |
| `contracts.generate_nda` | `contracts.agenerate_nda` | `nda_type`, `disclosing_party`, `receiving_party`, `purpose`, `confidentiality_period_years` | `jurisdiction`, `governing_law` | `nda_text`, `key_clauses_summary`, `legal_notes` |
| `contracts.generate_mou` | `contracts.agenerate_mou` | `party_a`, `party_b`, `objectives`, `responsibilities` | `duration_months`, `binding_sections`, `non_binding_statement` | `mou_text`, `binding_clauses`, `caution_notes` |

Notes:

- `gap_analysis` and `risk_score` require either `contract_text` or `contract_file`
- `generate_nda` supports `unilateral` and `mutual`
- `generate_mou` can distinguish binding sections from non-binding narrative

### `client.compliance`

Compliance use cases:

- create privacy policies
- check PDPL coverage on privacy notices or policies
- review VAT wording and tax treatment in a commercial document
- generate a pre-dispute legal demand letter

| Method | Async | Required inputs | Optional inputs | Returns |
|---|---|---|---|---|
| `compliance.generate_privacy_policy` | `compliance.agenerate_privacy_policy` | `company_name`, `service_type`, `third_party_sharing`, `international_transfers` | `data_collected`, `data_purposes`, `dpo_contact` | `policy_text`, `pdpl_compliance_score`, `sections_included`, `legal_notes` |
| `compliance.pdpl_check` | `compliance.apdpl_check` | - | `document_text`, `document_file`, `processing_context`, `cross_border_transfers` | `compliance_score`, `compliant_items`, `gaps`, `required_actions`, `summary` |
| `compliance.vat_check` | `compliance.avat_check` | - | `document_text`, `document_file`, `transaction_type`, `vat_rate` | `compliance_score`, `vat_treatment`, `detected_amounts`, `gaps`, `required_actions`, `summary` |
| `compliance.demand_letter` | `compliance.ademand_letter` | `sender_name`, `recipient_name`, `claim_type`, `incident_description`, `deadline_days`, `threat_of_action` | `claim_amount` | `letter_text`, `legal_notice_elements`, `strategic_notes` |

Notes:

- `pdpl_check` and `vat_check` require either inline text or a file
- `demand_letter` is the raw generator used directly and inside the pre-litigation workflow
- `generate_privacy_policy` is the raw generator used directly and inside privacy workflows

### `client.drafting`

Drafting use cases:

- improve legal language for clarity, formality, precision, brevity, or completeness
- summarize a legal text for obligations, rights, dates, money, and risks
- simplify dense legal Arabic for another audience
- pull clause structure without running the heavier legal extraction suite

| Method | Async | Required inputs | Optional inputs | Returns |
|---|---|---|---|---|
| `drafting.improve` | `drafting.aimprove` | `original_text`, `improvement_goals` | `context` | `improved_text`, `changes`, `overall_assessment`, `improvement_score` |
| `drafting.summarize` | `drafting.asummarize` | `summary_length` | `document_text`, `document_file`, `focus_on` | `summary`, `key_obligations`, `key_rights`, `key_dates`, `financial_terms`, `risk_highlights` |
| `drafting.simplify` | `drafting.asimplify` | `legal_text` | `target_audience` | `simplified_text`, `preserved_terms`, `reader_warnings` |
| `drafting.extract_clauses` | `drafting.aextract_clauses` | - | `document_text`, `document_file`, `document_type` | `clauses`, `extracted_clause_types`, `summary` |

Notes:

- `improvement_goals` can contain `clarity`, `formality`, `precision`, `brevity`, and `completeness`
- `summary_length` can be `brief`, `detailed`, or `executive`
- `summarize` and `extract_clauses` can work from a text file or PDF-backed file path

### `client.legal`

Atomic extraction use cases:

- classify unknown incoming documents
- extract parties, dates, money, obligations, termination, and dispute terms independently
- compose your own orchestration layer instead of using the built-in workflows

| Method | Async | Required inputs | Optional inputs | Returns |
|---|---|---|---|---|
| `legal.extract_clauses` | `legal.aextract_clauses` | - | `document_text`, `document_file`, `document_type` | `clauses`, `extracted_clause_types`, `summary` |
| `legal.extract_parties` | `legal.aextract_parties` | - | `document_text`, `document_file`, `document_type` | `parties`, `summary` |
| `legal.extract_dates` | `legal.aextract_dates` | - | `document_text`, `document_file`, `document_type` | `dates`, `summary` |
| `legal.extract_amounts` | `legal.aextract_amounts` | - | `document_text`, `document_file`, `document_type` | `amounts`, `summary` |
| `legal.extract_obligations` | `legal.aextract_obligations` | - | `document_text`, `document_file`, `document_type` | `obligations`, `summary` |
| `legal.extract_termination_terms` | `legal.aextract_termination_terms` | - | `document_text`, `document_file`, `document_type` | `termination_terms`, `summary` |
| `legal.extract_dispute_resolution` | `legal.aextract_dispute_resolution` | - | `document_text`, `document_file`, `document_type` | `dispute_resolution_terms`, `summary` |
| `legal.classify_document_type` | `legal.aclassify_document_type` | - | `document_text`, `document_file`, `document_type` | `primary_document_type`, `alternative_document_types`, `rationale`, `confidence_band`, `summary` |

Notes:

- all legal atomic tools share the same `LegalExtractionInput`
- they require at least one of `document_text` or `document_file`
- `document_type` is a hint, not a requirement
- `classify_document_type` returns `DocumentType` values such as `service_agreement`, `employment_contract`, `privacy_policy`, `policy`, `nda`, `mou`, `demand_letter`, and `unknown`

### `client.policies`

Policy and hiring use cases:

- generate HR policies for Saudi employers
- generate professional Arabic job descriptions with basic compliance checks

| Method | Async | Required inputs | Optional inputs | Returns |
|---|---|---|---|---|
| `policies.generate_hr_policy` | `policies.agenerate_hr_policy` | `policy_type`, `company_name`, `industry`, `employee_count` | `custom_requirements` | `policy_text`, `saudi_law_compliance_notes`, `mandatory_inclusions_met`, `recommended_additions` |
| `policies.job_description` | `policies.ajob_description` | `job_title`, `department`, `required_experience_years`, `required_education`, `saudization_preferred` | `key_responsibilities`, `required_skills`, `salary_range` | `job_description_text`, `discriminatory_language_flags`, `saudization_statement`, `legal_compliance_notes` |

## Workflow Reference

Workflows are higher-signal than one isolated tool because they accumulate shared `WorkflowState`, findings, references, evidence, and generated artifacts across steps.

| Method | Async | Required inputs | Optional inputs | Returns |
|---|---|---|---|---|
| `workflow.contract_review` | `workflow.acontract_review` | - | `shared_runtime`, `step_runtime_overrides`, `document_text`, `document_file`, `document_type`, `contract_type`, `include_redlines` | `state`, `executive_summary`, `risk_score`, `risk_level`, `missing_mandatory_clauses`, `amendment_recommendations`, `optional_redlines` |
| `workflow.employment_review` | `workflow.aemployment_review` | - | `shared_runtime`, `step_runtime_overrides`, `document_text`, `document_file`, `document_type`, `contract_type`, `probation_days`, `extension_in_writing`, `monthly_salary`, `years_of_service`, `termination_reason` | `state`, `executive_summary`, `probation_status`, `end_of_service_amount`, `employment_risks`, `recommended_follow_ups` |
| `workflow.privacy_compliance_review` | `workflow.aprivacy_compliance_review` | - | `shared_runtime`, `step_runtime_overrides`, `document_text`, `document_file`, `document_type`, `processing_context`, `cross_border_transfers`, `generate_policy_draft`, `company_name`, `service_type`, `data_collected`, `data_purposes`, `third_party_sharing`, `international_transfers`, `dpo_contact` | `state`, `executive_summary`, `compliance_score`, `key_gaps`, `remediation_priorities`, `policy_draft_text` |
| `workflow.pre_litigation_notice` | `workflow.apre_litigation_notice` | `sender_name`, `recipient_name`, `claim_type`, `incident_description`, `deadline_days`, `threat_of_action` | `shared_runtime`, `step_runtime_overrides`, `support_document_text`, `support_document_file`, `support_document_type`, `contract_type`, `claim_amount` | `state`, `executive_summary`, `demand_letter_text`, `claim_support_summary`, `negotiation_points` |
| `workflow.policy_generation_review` | `workflow.apolicy_generation_review` | `policy_kind` | `shared_runtime`, `step_runtime_overrides`, `policy_type`, `company_name`, `industry`, `employee_count`, `custom_requirements`, `job_title`, `department`, `required_experience_years`, `required_education`, `key_responsibilities`, `required_skills`, `saudization_preferred`, `salary_range`, `service_type`, `data_collected`, `data_purposes`, `third_party_sharing`, `international_transfers`, `dpo_contact` | `state`, `policy_kind`, `executive_summary`, `generated_text`, `review_notes`, `follow_up_actions` |

### `workflow.contract_review`

Step sequence:

1. `legal.classify_document_type`
2. `legal.extract_clauses`
3. `legal.extract_parties`
4. `legal.extract_dates`
5. `legal.extract_amounts`
6. `legal.extract_obligations`
7. `legal.extract_termination_terms`
8. `legal.extract_dispute_resolution`
9. `contracts.gap_analysis`
10. `contracts.risk_score`
11. synthesis for reference mapping and amendment recommendations
12. optional redline generation when `include_redlines=True`

Best use cases:

- full contract review instead of a single gap score
- triage when you need both clause extraction and a final risk position
- producing amendment recommendations and optional redline hints

### `workflow.employment_review`

Step sequence:

1. legal classification and extraction over the employment document
2. optional `labor.probation_check` when `probation_days` is provided
3. optional `labor.end_of_service` when `monthly_salary`, `years_of_service`, and `termination_reason` are all provided
4. synthesis of employment risks and follow-up actions

Best use cases:

- reviewing an employment contract with labor-rights questions
- combining document understanding with deterministic labor calculations
- answering probation and end-of-service questions from one workflow result

### `workflow.privacy_compliance_review`

Step sequence:

1. `legal.classify_document_type`
2. `drafting.extract_clauses`
3. `compliance.pdpl_check` on the original text
4. optional `compliance.generate_privacy_policy` when `generate_policy_draft=True`
5. optional second `compliance.pdpl_check` on the generated draft
6. synthesis of remediation priorities

Best use cases:

- measuring the current privacy document
- generating a remediation draft and immediately re-checking it
- producing a gap list plus a next-action list

Required branch note:

- if `generate_policy_draft=True`, you must provide `company_name` and `service_type`

### `workflow.pre_litigation_notice`

Step sequence:

1. optional supporting-document analysis when support text or file is supplied
2. `compliance.demand_letter`
3. `drafting.improve` over the generated letter
4. synthesis of claim-support signals and negotiation points

Best use cases:

- generating a practical notice from facts alone
- generating a stronger notice when you also have a supporting contract or evidence document
- combining extracted obligations, amounts, and dates with letter drafting

Branch note:

- if no support document is supplied, the workflow still runs and produces the notice from facts alone

### `workflow.policy_generation_review`

This workflow has three branches selected by `policy_kind`.

`policy_kind="hr_policy"`:

- requires `policy_type`, `company_name`, `industry`, `employee_count`
- generates an HR policy
- reviews it with `drafting.extract_clauses`
- summarizes it with `drafting.summarize`

`policy_kind="job_description"`:

- requires `job_title`, `department`, `required_education`, `required_experience_years`
- generates a job description
- improves it with `drafting.improve`
- returns review notes and follow-up actions

`policy_kind="privacy_policy"`:

- requires `company_name`, `service_type`
- generates a privacy policy
- re-checks it with `compliance.pdpl_check`
- returns review notes and follow-up actions

## Agent Runtime Reference

The agent runtime is deterministic. It never chooses arbitrary raw tools. It plans only against the approved workflow registry.

### Public Methods

| Method | Purpose |
|---|---|
| `client.agent.list_capabilities()` | Returns fixed `AgentCapabilityMetadata` entries |
| `client.agent.plan(...)` | Builds a deterministic `AgentPlan` without execution |
| `client.agent.run(...)` | Plans and executes synchronously |
| `await client.agent.arun(...)` | Plans and executes asynchronously |

### `AgentRunInput`

Fields:

- `goal`
- `scenario_hint`
- `documents`
- `facts`
- `shared_runtime`
- `step_runtime_overrides`

Each `documents` item supports:

- `name`
- `text`
- `file_path`
- `document_type`
- `role` as `primary` or `supporting`

Rules:

- each agent document must contain either `text` or `file_path`
- if no explicit primary document exists, the first document is treated as primary
- if no explicit supporting document exists, pre-litigation payload building falls back to the primary document
- `scenario_hint` overrides automatic scenario detection

### Automatic Scenario Selection

| Scenario | Triggered by goal language | Planned capability path |
|---|---|---|
| `contract_dispute_notice` | demand, claim, notice, dispute | `workflow.contract_review` -> `workflow.pre_litigation_notice` |
| `employment_rights_review` | employment, labor, probation, end of service | `workflow.employment_review` |
| `privacy_remediation` | privacy, data, PDPL | `workflow.privacy_compliance_review` |
| `policy_creation_review` | policy, job description | `workflow.policy_generation_review` |
| `contract_review_only` | contract, agreement | `workflow.contract_review` |
| `unknown` | no safe match | no execution; blocked plan |

### Facts By Scenario

`contract_review_only`:

- `contract_type`
- `include_redlines`

`contract_dispute_notice`:

- all contract-review facts above
- `sender_name`
- `recipient_name`
- `claim_type`
- `claim_amount`
- `incident_description`
- `deadline_days`
- `threat_of_action`

`employment_rights_review`:

- `contract_type`
- `probation_days`
- `extension_in_writing`
- `monthly_salary`
- `years_of_service`
- `termination_reason`

`privacy_remediation`:

- `processing_context`
- `cross_border_transfers`
- `generate_policy_draft`
- `company_name`
- `service_type`
- `data_collected`
- `data_purposes`
- `third_party_sharing`
- `international_transfers`
- `dpo_contact`

`policy_creation_review`:

- `policy_kind`
- plus the branch-specific workflow inputs for `hr_policy`, `job_description`, or `privacy_policy`

### Agent Status Values

| Status | Meaning |
|---|---|
| `completed` | All planned capabilities ran and passed guardrails |
| `needs_more_information` | Execution stopped safely because required inputs were missing |
| `blocked` | No safe scenario was chosen or a guardrail blocked execution |

When status is `needs_more_information`:

- `next_question` is populated
- `state.missing_inputs` is populated
- completed workflow capabilities remain available in `state.completed_capabilities`

When agent logging is enabled:

- `run_id` is populated
- `log_path` points to a dated JSONL trace file

## MCP Server Reference

The MCP server intentionally exposes a curated subset of the SDK, not the full internal surface.

### Start The Server

```bash
python -m pip install --upgrade "qanuni-sdk[mcp]"
set QANUNI_MCP_AUTH_TOKEN=change-this-long-random-token
qanuni-mcp-server serve --host 127.0.0.1 --port 8088
```

Default endpoints:

- health check: `http://127.0.0.1:8088/healthz`
- MCP streamable HTTP: `http://127.0.0.1:8088/mcp/`

Auth and governance behavior:

- bearer auth is required by default
- `/healthz` stays open by default
- rate limiting is enabled
- each call is audit logged when audit logging is configured

### Curated MCP Tools

| MCP tool | SDK surface | Kind | Required inputs | Produces |
|---|---|---|---|---|
| `workflow_contract_review` | `workflow.contract_review` | workflow | `document_text` or `document_file` | `workflow_state`, `risk_score`, `missing_mandatory_clauses`, `amendment_recommendations` |
| `workflow_pre_litigation_notice` | `workflow.pre_litigation_notice` | workflow | `sender_name`, `recipient_name`, `claim_type`, `incident_description`, `deadline_days`, `threat_of_action` | `workflow_state`, `demand_letter`, `claim_support_summary`, `negotiation_points` |
| `legal_classify_document_type` | `legal.classify_document_type` | atomic tool | `document_text` or `document_file` | `document_type_classification` |
| `legal_extract_clauses` | `legal.extract_clauses` | atomic tool | `document_text` or `document_file` | `clauses`, `clause_types` |
| `legal_extract_parties` | `legal.extract_parties` | atomic tool | `document_text` or `document_file` | `parties` |
| `legal_extract_dates` | `legal.extract_dates` | atomic tool | `document_text` or `document_file` | `dates` |
| `legal_extract_amounts` | `legal.extract_amounts` | atomic tool | `document_text` or `document_file` | `amounts` |
| `legal_extract_obligations` | `legal.extract_obligations` | atomic tool | `document_text` or `document_file` | `obligations` |
| `legal_extract_termination_terms` | `legal.extract_termination_terms` | atomic tool | `document_text` or `document_file` | `termination_terms` |
| `legal_extract_dispute_resolution` | `legal.extract_dispute_resolution` | atomic tool | `document_text` or `document_file` | `dispute_resolution_terms` |
| `contracts_risk_score` | `contracts.risk_score` | atomic tool | `contract_text` or `contract_file` | `risk_score`, `mitigation_priorities` |
| `compliance_demand_letter` | `compliance.demand_letter` | atomic tool | `sender_name`, `recipient_name`, `claim_type`, `incident_description`, `deadline_days`, `threat_of_action` | `demand_letter`, `strategic_notes` |

### MCP Resources

Legal-reference resources:

- `qanuni://references/catalog`
- `qanuni://references/{packet_key}`

Run-trace resources:

- `qanuni://runs`
- `qanuni://runs/{run_id}/output`
- `qanuni://runs/{run_id}/state`
- `qanuni://runs/{run_id}/findings`
- `qanuni://runs/{run_id}/artifacts/{artifact_name}`

Execution envelopes return:

- `run_id`
- `surface_id`
- `tool_name`
- `kind`
- `summary`
- `output`
- `resource_uris.output_uri`
- optional `resource_uris.state_uri`
- optional `resource_uris.findings_uri`
- optional `resource_uris.artifact_uris`
- `resource_uris.legal_reference_uris`

## Caching, Observability, And Governance

### Selective Cache Policy

Enable caching with:

```bash
QANUNI_CACHE_ENABLED=true
```

Cached tool surfaces:

- `legal.classify_document_type`
- `legal.extract_clauses`
- `legal.extract_parties`
- `legal.extract_dates`
- `legal.extract_amounts`
- `legal.extract_obligations`
- `legal.extract_termination_terms`
- `legal.extract_dispute_resolution`
- `drafting.extract_clauses`
- `drafting.summarize`
- `drafting.simplify`
- `contracts.gap_analysis`
- `contracts.risk_score`
- `compliance.pdpl_check`
- `compliance.vat_check`

Cached workflow surfaces:

- `workflow.contract_review`
- `workflow.employment_review`
- `workflow.privacy_compliance_review`

Generator-style calls intentionally bypass the selective cache. For example, repeated NDA generation still calls the provider each time.

### Observability

Use `client.observability.snapshot()` to inspect in-memory events and `client.observability.clear()` to reset them.

Observed metrics include:

- success or failure status
- `scope_type` and `scope_id`
- latency
- input, output, and total tokens
- estimated cost
- cache status
- error code on failures

Built-in pricing is bundled. You only need `QANUNI_MODEL_PRICING_FILE` when you want to override the catalog.

### Governed Assets

The SDK can validate its packaged prompt and legal-reference assets at startup.

Commands:

```bash
qanuni-governance validate-assets
qanuni-governance write-assets
```

Disable startup validation only when you intentionally need it:

```bash
QANUNI_ASSET_MANIFEST_ENFORCED=false
```

## Error Model

All structured SDK failures inherit from `QanuniError` and expose:

- `error_code`
- `details`
- `to_dict()`

Common error codes:

| Code | Typical cause |
|---|---|
| `QANUNI_CONFIG_API_KEY_MISSING` | prompt-backed tool called without a usable provider key |
| `QANUNI_VALIDATION_INPUT_CONFLICT` | mixed positional `data` with kwargs |
| `QANUNI_VALIDATION_INPUT_TYPE` | wrong payload type |
| `QANUNI_VALIDATION_DOCUMENT_SOURCE_MISSING` | text/file source missing |
| `QANUNI_VALIDATION_DOCUMENT_PATH_MISSING` | file path does not exist |
| `QANUNI_OUTPUT_SCHEMA_MISMATCH` | provider output did not satisfy the schema |
| `QANUNI_API_PROVIDER_FAILURE` | upstream model request failed |
| `QANUNI_API_RESPONSE_INCOMPLETE` | provider stopped before producing usable output |
| `QANUNI_API_RESPONSE_REFUSAL` | provider returned a refusal |
| `QANUNI_MCP_AUTH_REQUIRED` | MCP request missing or invalid auth |
| `QANUNI_MCP_RATE_LIMITED` | MCP rate limit exceeded |
| `QANUNI_MCP_RUN_NOT_FOUND` | requested MCP run does not exist |
| `QANUNI_MCP_RESOURCE_NOT_FOUND` | requested MCP resource does not exist |
| `QANUNI_FEATURE_NOT_READY` | async or other feature not implemented on that surface |

## Commands

| Command | Purpose |
|---|---|
| `qanuni-acceptance --list` | list acceptance scenarios |
| `qanuni-acceptance --mode mocked` | run the acceptance pack offline |
| `qanuni-mcp-smoke --mode mocked` | exercise the curated MCP surface |
| `qanuni-examples --list` | list runnable examples |
| `qanuni-governance validate-assets` | validate governed assets |
| `qanuni-release-check --allow-dirty` | run packaging/release checks |
| `qanuni-mcp-server serve --host 127.0.0.1 --port 8088` | serve the MCP endpoint |

## Examples And Guides

- runnable examples: [examples/README.md](examples/README.md)
- agent legal-task scenarios: [examples/LEGAL_TASKS.md](examples/LEGAL_TASKS.md)
- user guide: [docs/guides/README_USERS.md](docs/guides/README_USERS.md)
- acceptance guide: [docs/guides/README_ACCEPTANCE.md](docs/guides/README_ACCEPTANCE.md)
- publishing guide: [docs/guides/README_PUBLISHING.md](docs/guides/README_PUBLISHING.md)
- prompt authoring notes: [docs/08_PROMPT_AUTHORING.md](docs/08_PROMPT_AUTHORING.md)

## Deterministic Vs Prompt-Backed Summary

No OpenAI key required:

- `labor.end_of_service`
- `labor.probation_check`

OpenAI key or custom provider required:

- all other tool calls
- all workflows
- all agent runs
- MCP surfaces that wrap prompt-backed tools or workflows
