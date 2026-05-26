# Qanuni SDK Free Edition

Qanuni is an Arabic-first Python SDK for Saudi legal workflows. This folder packages the current toolset as a **fully free distribution**: no activation, no license token, no seat control, and no premium gate. If a user has their own OpenAI key, they can use the prompt-backed tools immediately. Deterministic tools work even without OpenAI.

## What Makes This Edition Different?

- all shipped tools are free
- async usage is also free
- no `client.license` surface
- no activation flow
- no owner-side licensing service
- same package name for publishing: `qanuni-sdk`

## Included Guides

- full walkthrough: [FullReadme.md](FullReadme.md)
- human-testing examples: [examples/README.md](examples/README.md)
- user guide: [docs/guides/README_USERS.md](docs/guides/README_USERS.md)
- acceptance guide: [docs/guides/README_ACCEPTANCE.md](docs/guides/README_ACCEPTANCE.md)
- publishing guide: [docs/guides/README_PUBLISHING.md](docs/guides/README_PUBLISHING.md)
- prompt authoring notes: [docs/08_PROMPT_AUTHORING.md](docs/08_PROMPT_AUTHORING.md)
- legal-agent phase 1 notes: [docs/10_LEGAL_AGENT_PHASE_ONE.md](docs/10_LEGAL_AGENT_PHASE_ONE.md)
- legal-agent phase 2 notes: [docs/11_LEGAL_AGENT_PHASE_TWO.md](docs/11_LEGAL_AGENT_PHASE_TWO.md)
- legal-agent phase 3 notes: [docs/12_LEGAL_AGENT_PHASE_THREE.md](docs/12_LEGAL_AGENT_PHASE_THREE.md)
- legal-agent phase 4 notes: [docs/13_LEGAL_AGENT_PHASE_FOUR.md](docs/13_LEGAL_AGENT_PHASE_FOUR.md)
- legal-agent phase 5 notes: [docs/14_LEGAL_AGENT_PHASE_FIVE.md](docs/14_LEGAL_AGENT_PHASE_FIVE.md)
- legal-agent phase 6 notes: [docs/15_LEGAL_AGENT_PHASE_SIX.md](docs/15_LEGAL_AGENT_PHASE_SIX.md)

## Shipped Toolset

- `labor.end_of_service`
- `labor.probation_check`
- `labor.generate_contract`
- `legal.classify_document_type`
- `legal.extract_clauses`
- `legal.extract_parties`
- `legal.extract_dates`
- `legal.extract_amounts`
- `legal.extract_obligations`
- `legal.extract_termination_terms`
- `legal.extract_dispute_resolution`
- `contracts.gap_analysis`
- `contracts.risk_score`
- `contracts.generate_nda`
- `contracts.generate_mou`
- `compliance.pdpl_check`
- `compliance.vat_check`
- `drafting.extract_clauses`
- `drafting.improve`
- `drafting.summarize`
- `drafting.simplify`
- `compliance.generate_privacy_policy`
- `compliance.demand_letter`
- `policies.generate_hr_policy`
- `policies.job_description`

## Shipped Workflows

- `workflow.contract_review`
- `workflow.employment_review`
- `workflow.privacy_compliance_review`
- `workflow.pre_litigation_notice`
- `workflow.policy_generation_review`

## Shipped Agent Runtime

- `client.agent.list_capabilities()`
- `client.agent.plan(...)`
- `client.agent.run(...)`
- `client.agent.arun(...)`

## Shipped MCP Server Surface

- workflows: `workflow_contract_review`, `workflow_pre_litigation_notice`
- atomic tools: `legal_classify_document_type`, `legal_extract_clauses`, `legal_extract_parties`, `legal_extract_dates`, `legal_extract_amounts`, `legal_extract_obligations`, `legal_extract_termination_terms`, `legal_extract_dispute_resolution`, `contracts_risk_score`, `compliance_demand_letter`
- resources: `qanuni://references/*`, `qanuni://runs/*`

## Quickstart

If you are using the published package:

```bash
python -m pip install --upgrade qanuni-sdk
```

If you are validating this repository locally before publishing, install the source
from [free_edition](/E:/Private/Nawaf/BandAI_SDK/free_edition) instead:

```bash
cd free_edition
python -m pip install -e .
```

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

```python
import os

from dotenv import load_dotenv
from qanuni import LegalClient

load_dotenv()
client = LegalClient(api_key=os.getenv("OPENAI_API_KEY"))

result = client.drafting.improve(
    original_text="يدفع الطرف الأول عند الإنجاز.",
    improvement_goals=["precision", "clarity"],
    context="service agreement",
)

print(result.improved_text)
```

## Bundled Commands

```bash
qanuni-acceptance --list
qanuni-acceptance --mode mocked
qanuni-examples --list
qanuni-examples --category mocked_local
qanuni-mcp-smoke --mode mocked
qanuni-release-check --allow-dirty
qanuni-mcp-server serve --host 127.0.0.1 --port 8088
```

## Acceptance Pack

The free edition now ships with a black-box acceptance surface meant for real user
validation before rollout:

- packaged Arabic sample documents
- an offline mocked acceptance runner
- a live acceptance runner for quota-backed checks
- an external MCP smoke test
- a clean notebook: [AcceptancePack.ipynb](AcceptancePack.ipynb)

Start with:

```bash
qanuni-acceptance --mode mocked
```

If you want literal step-by-step human test scripts instead of one consolidated runner,
use the verbose example suite in [examples/README.md](examples/README.md):

```bash
python examples/example_00_environment_and_catalog.py
python examples/example_03_contract_review_workflow.py
python examples/example_06_agent_contract_dispute_notice.py
```

Then, if the MCP extra is installed:

```bash
qanuni-mcp-smoke --mode mocked
```

## MCP Server

Install the optional MCP extra:

```bash
python -m pip install "qanuni-sdk[mcp]"
```

Or from the repository source:

```bash
cd free_edition
python -m pip install -e .[mcp]
```

Set a bearer token:

```bash
QANUNI_MCP_AUTH_TOKEN=change-this-long-random-token
```

Then serve the curated MCP endpoint:

```bash
qanuni-mcp-server serve --host 127.0.0.1 --port 8088
```

The default HTTP endpoints are:

- health: `http://127.0.0.1:8088/healthz`
- MCP: `http://127.0.0.1:8088/mcp/`

## Configuration

Minimal `.env`:

```bash
OPENAI_API_KEY=sk-...
QANUNI_MODEL=gpt-5-mini
QANUNI_LANGUAGE=ar
QANUNI_JURISDICTION=SA
QANUNI_TIMEOUT=60
QANUNI_MAX_RETRIES=0
```

Optional global overrides when you intentionally want one hard cap for every tool:

```bash
QANUNI_MAX_OUTPUT_TOKENS=3200
QANUNI_REASONING_EFFORT=low
QANUNI_VERBOSITY=low
```

For faster notebook feedback, keep retries at `0`. The SDK now makes a single
provider attempt by default and does not run hidden structured-output recovery
calls. Leave `QANUNI_MAX_OUTPUT_TOKENS` unset unless you intentionally want a
global cap, because long-form generators such as NDA, MOU, and privacy-policy
tools rely on larger tool-specific defaults.

Built-in pricing:

- the SDK now ships with a bundled pricing catalog by default
- `estimated_cost_usd` is calculated automatically for supported models such as `gpt-5-mini`
- `QANUNI_MODEL_PRICING_FILE` is now an optional override, not a requirement

Canonical custom pricing format:

```yaml
models:
  gpt-5-mini:
    input_cost_per_1m_usd: 0.25
    output_cost_per_1m_usd: 2.00
```

Backward compatibility:

- older `input_cost_per_1k_usd` and `output_cost_per_1k_usd` keys are still accepted
- internally the SDK now normalizes pricing to `per_1m`

In notebooks, prefer:

```python
%pip install --upgrade qanuni-sdk
```

Then restart the kernel and verify:

```python
import qanuni

print(qanuni.__version__)
print(qanuni.__file__)
```

YAML config loading still works:

```python
from qanuni import LegalClient

client = LegalClient.from_config(".qanuni.yaml")
```

## Publishing Note

This free edition is designed to be published under the **same project name** `qanuni-sdk`, but as a **new version** such as `0.2.5`. The publishing checklist lives in [docs/guides/README_PUBLISHING.md](docs/guides/README_PUBLISHING.md).
