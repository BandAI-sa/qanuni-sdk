# Qanuni SDK

Qanuni is an Arabic-first Python SDK for Saudi legal workflows.

This build is the **fully free distribution**:

- no activation
- no license token
- no premium gate
- all shipped tools are available immediately

Users bring their own OpenAI API key for prompt-backed tools. Deterministic tools such as Saudi labor calculations work without OpenAI.

## Install

```bash
python -m pip install --upgrade qanuni-sdk
```

## Quickstart

```python
import os

from dotenv import load_dotenv
from qanuni import LegalClient

load_dotenv()
client = LegalClient(api_key=os.getenv("OPENAI_API_KEY"))

benefit = client.labor.end_of_service(
    monthly_salary=12000,
    years_of_service=7.5,
    termination_reason="resignation",
    contract_type="indefinite",
)

print(benefit.total_amount)
```

```python
result = client.contracts.gap_analysis(
    contract_text="يلتزم الطرف الثاني بتنفيذ الأعمال، ويتم السداد لاحقًا.",
    contract_type="service_agreement",
)

print(result.summary)
```

## Included Tools

- `labor.end_of_service`
- `labor.probation_check`
- `contracts.gap_analysis`
- `contracts.generate_nda`
- `contracts.generate_mou`
- `drafting.improve`
- `drafting.summarize`
- `drafting.simplify`
- `compliance.generate_privacy_policy`
- `compliance.demand_letter`
- `policies.generate_hr_policy`
- `policies.job_description`

## Examples Command

```bash
qanuni-examples --list
qanuni-acceptance --list
qanuni-acceptance --mode mocked
```

## Optional MCP Extra

To expose the SDK through an MCP server for external agentic clients:

```bash
python -m pip install "qanuni-sdk[mcp]"
```

Then configure:

```bash
QANUNI_MCP_AUTH_TOKEN=change-this-long-random-token
```

And serve:

```bash
qanuni-mcp-server serve --host 127.0.0.1 --port 8088
```

To smoke-test the curated MCP surface after installing the extra:

```bash
qanuni-mcp-smoke --mode mocked
```

## Default Behavior

- Arabic-first prompts and outputs
- Saudi-oriented legal framing
- structured Pydantic outputs
- async methods available in this free build
