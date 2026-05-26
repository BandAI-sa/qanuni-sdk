# Full Qanuni Free Edition Walkthrough

This file is the complete journey for a first-time user of the **free Qanuni SDK distribution**.

In this edition:

- all shipped tools are free
- there is no activation flow
- there is no `license_token`
- there is no `client.license`
- async methods are also available

The only external credential you may need is your own `OPENAI_API_KEY` for prompt-backed tools.
Do not place the API key directly inside notebook cells. Prefer `.env` or environment variables.

## 1. Install the Package

If you are using the already published package:

```bash
python -m pip install --upgrade qanuni-sdk
```

If you are validating this repository locally before publishing, move into
`free_edition` and install the local source instead of pulling the older PyPI release:

```bash
cd free_edition
python -m pip install -e .
```

Inside Jupyter, prefer:

```python
%pip install --upgrade qanuni-sdk
```

If you are installing from the repository source inside Jupyter:

```python
%pip install -e .
```

After any install or upgrade inside Jupyter, restart the kernel once before
running the next cells.

Import name:

```python
from qanuni import LegalClient
```

Package name and import name are different on purpose:

- package on PyPI: `qanuni-sdk`
- import in Python: `qanuni`

Quick sanity check:

```python
import qanuni

print(qanuni.__version__)
print(qanuni.__file__)
```

If you still see an older version such as `0.1.0`, the notebook is not using
the package version you expect yet.

## 1.1 Optional MCP Extra

If you want to expose the SDK to another agent through MCP, install the MCP extra:

```bash
python -m pip install "qanuni-sdk[mcp]"
```

From this repository source:

```bash
cd free_edition
python -m pip install -e .[mcp]
```

## 2. Optional `.env` Setup

Create a local `.env`:

```bash
OPENAI_API_KEY=sk-...
QANUNI_MODEL=gpt-5-mini
QANUNI_LANGUAGE=ar
QANUNI_JURISDICTION=SA
QANUNI_TIMEOUT=60
QANUNI_MAX_RETRIES=0
```

Optional global overrides if you intentionally want one shared cap across all tools:

```bash
QANUNI_MAX_OUTPUT_TOKENS=3200
QANUNI_REASONING_EFFORT=low
QANUNI_VERBOSITY=low
QANUNI_CACHE_ENABLED=false
QANUNI_CACHE_TTL_SECONDS=86400
QANUNI_OBSERVABILITY_PERSIST=false
```

You can also pass everything directly in code, but never paste the literal
placeholder `sk-...` into a real notebook cell.

Performance note:

- `QANUNI_MODEL` now remains under your control and is no longer overridden by prompt defaults.
- Start with `QANUNI_MAX_RETRIES=0` in notebooks so timeout failures return quickly.
- The SDK now uses a single provider attempt by default and does not perform hidden structured-output recovery calls.
- Leave `QANUNI_MAX_OUTPUT_TOKENS` unset unless you intentionally want one global cap, because long-form generators use larger tool-specific defaults.
- For long-form generation, prefer raising `timeout_seconds` before raising `max_output_tokens`.

Optional MCP server settings:

```bash
QANUNI_MCP_AUTH_TOKEN=change-this-long-random-token
QANUNI_MCP_HOST=127.0.0.1
QANUNI_MCP_PORT=8088
QANUNI_MCP_RATE_LIMIT_WINDOW_SECONDS=60
QANUNI_MCP_RATE_LIMIT_MAX_REQUESTS=60
QANUNI_MCP_AUDIT_LOG_PATH=.qanuni_audit/qanuni_mcp_audit.jsonl
```

## 3. Create Your First Client

If you only want deterministic labor tools:

```python
from qanuni import LegalClient

client = LegalClient()
```

If you want prompt-backed tools:

```python
import os

from dotenv import load_dotenv
from qanuni import LegalClient

load_dotenv()
client = LegalClient(api_key=os.getenv("OPENAI_API_KEY"))
```

## 4. Inspect the Tool Catalog

```python
from qanuni import LegalClient

client = LegalClient()

for tool in client.list_tools():
    print(tool.tool_id, tool.tier, tool.implementation)
```

You can also inspect availability:

```python
for tool in client.list_tool_access():
    print(tool.tool_id, tool.available, tool.reason)
```

In this free edition, all shipped tools should be available.

## 5. Use Deterministic Tools Without OpenAI

### End of service

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
print(result.calculation_breakdown)
print(result.legal_explanation)
print(result.additional_entitlements)
```

### Probation check

```python
result = client.labor.probation_check(
    probation_days=120,
    extension_in_writing=True,
)

print(result.is_legal)
print(result.max_allowed_days)
print(result.violations)
```

## 6. Use Prompt-Backed Tools With OpenAI

### Improve drafting

```python
result = client.drafting.improve(
    original_text="يدفع الطرف الأول عند الإنجاز.",
    improvement_goals=["precision", "clarity", "formality"],
    context="service agreement",
)

print(result.improved_text)
print(result.changes)
```

### Summarize a legal document

```python
result = client.drafting.summarize(
    document_text="""
    يتعهد الطرف الأول بتقديم الخدمات التقنية،
    ويلتزم الطرف الثاني بسداد المقابل وفق الفواتير الصادرة،
    ويجوز إنهاء الاتفاق عند الإخلال الجسيم.
    """,
    summary_length="executive",
)

print(result.summary)
print(result.key_obligations)
print(result.risk_highlights)
```

### Simplify legal Arabic

```python
result = client.drafting.simplify(
    legal_text="يلتزم الموظف بعدم منافسة صاحب العمل خلال المدة المنصوص عليها تعاقديًا."
)

print(result.simplified_text)
```

## 7. Contract and Commercial Tools

### Contract gap analysis

```python
result = client.contracts.gap_analysis(
    contract_text="""
    يلتزم الطرف الثاني بتنفيذ الأعمال،
    ويتم السداد لاحقًا وفق ما يراه الطرف الأول مناسبًا،
    ويجوز إنهاء العقد عند الحاجة.
    """,
    contract_type="service_agreement",
)

print(result.summary)
print(result.gaps)
print(result.missing_mandatory_clauses)
```

### Generate NDA

```python
result = client.contracts.generate_nda(
    nda_type="mutual",
    disclosing_party="شركة ألف",
    receiving_party="شركة باء",
    purpose="دراسة شراكة تشغيلية",
    confidentiality_period_years=3,
    _config=ToolRuntimeConfig(
        model="gpt-5-mini",
        timeout_seconds=45,
        max_output_tokens=2200,
        verbosity="low",
    ),
)

print(result.nda_text)
```

### Generate MOU

```python
result = client.contracts.generate_mou(
    party_a="شركة ألف",
    party_b="شركة باء",
    objectives=["تطوير منصة قانونية مشتركة"],
    responsibilities=["تبادل المتطلبات", "تجهيز خطة تنفيذ أولية"],
    duration_months=6,
    binding_sections=["السرية", "القانون الحاكم"],
)

print(result.mou_text)
```

## 8. Compliance and Policy Tools

### Privacy policy

```python
result = client.compliance.generate_privacy_policy(
    company_name="شركة تقنية سعودية",
    service_type="منصة SaaS",
    data_collected=["الاسم", "الهاتف", "البريد الإلكتروني", "بيانات الاستخدام"],
    data_purposes=["تشغيل الخدمة", "التحقق", "الدعم", "الأمن"],
    third_party_sharing=False,
    international_transfers=False,
)

print(result.policy_text)
print(result.pdpl_compliance_score)
```

### Demand letter

```python
result = client.compliance.demand_letter(
    sender_name="شركة ألف",
    recipient_name="شركة باء",
    claim_type="مستحقات تعاقدية",
    claim_amount=85000,
    incident_description="تأخر في سداد مستحقات عقد خدمات تقنية.",
    deadline_days=7,
    threat_of_action="سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد.",
)

print(result.letter_text)
```

### HR policy

```python
result = client.policies.generate_hr_policy(
    policy_type="الغياب والانضباط",
    company_name="شركة تجريبية",
    industry="خدمات تقنية",
    employee_count=45,
    custom_requirements=["اعتماد التدرج التأديبي", "تحديد آلية التوثيق"],
)

print(result.policy_text)
```

### Job description

```python
result = client.policies.job_description(
    job_title="أخصائي التزام",
    department="الشؤون القانونية",
    required_experience_years=2,
    required_education="بكالوريوس قانون",
    key_responsibilities=["إعداد التقارير", "متابعة السياسات", "مراجعة المخاطر"],
    required_skills=["التحليل", "صياغة السياسات", "المراجعة القانونية"],
    saudization_preferred=True,
)

print(result.job_description_text)
```

## 9. Async Is Free in This Edition

```python
import asyncio


async def main() -> None:
    result = await client.drafting.aimprove(
        original_text="يدفع الطرف الأول عند الإنجاز.",
        improvement_goals=["precision", "clarity"],
        context="service agreement",
    )
    print(result.improved_text)


asyncio.run(main())
```

## 10. Local Mocked Exploration Without OpenAI

The package ships `examples.py` as a mini lab:

```bash
qanuni-examples --list
qanuni-examples --category mocked_local
qanuni-examples labor_end_of_service
```

This is useful when you want to:

- explore outputs
- verify installation
- write docs
- test the package without API cost

## 11. Fixed Workflows

The free edition now also exposes fixed orchestration workflows through:

```python
client.workflow
```

### Contract review workflow

```python
result = client.workflow.contract_review(
    document_text="""
    يلتزم الطرف الثاني بتنفيذ الأعمال،
    ويتم السداد خلال 15 يومًا من الفاتورة،
    ويجوز إنهاء العقد بعد إشعار مكتوب.
    """,
    contract_type="service_agreement",
    include_redlines=True,
)

print(result.executive_summary)
print(result.amendment_recommendations)
print(result.state.steps)
```

### Employment review workflow

```python
result = client.workflow.employment_review(
    document_text="عقد عمل يحدد الراتب والمهام والإجازات وشرط الإنهاء.",
    probation_days=120,
    extension_in_writing=False,
    monthly_salary=12000,
    years_of_service=3.5,
    termination_reason="contract_completion",
    contract_type="indefinite",
)

print(result.executive_summary)
print(result.probation_status)
print(result.end_of_service_amount)
```

### Privacy compliance review workflow

```python
result = client.workflow.privacy_compliance_review(
    document_text="توضح السياسة أغراض المعالجة دون آلية واضحة لطلبات أصحاب البيانات.",
    processing_context="منصة رقمية",
    generate_policy_draft=True,
    company_name="شركة ألف",
    service_type="منصة تقنية",
)

print(result.executive_summary)
print(result.compliance_score)
print(result.remediation_priorities)
```

## 12. Legal Agent Runtime

The free edition now includes a deterministic legal agent above the workflows:

```python
result = client.agent.run(
    goal="راجع العقد ثم جهز خطاب مطالبة قبل النزاع للمبالغ المتأخرة.",
    documents=[
        {
            "text": "يلتزم الطرف الثاني بتنفيذ الأعمال ويتم السداد خلال 15 يومًا.",
            "document_type": "service_agreement",
        }
    ],
    facts={
        "contract_type": "service_agreement",
        "sender_name": "شركة ألف",
        "recipient_name": "شركة باء",
        "claim_type": "مستحقات تعاقدية",
        "claim_amount": 85000,
        "incident_description": "تأخر السداد رغم حلول الأجل.",
        "deadline_days": 7,
        "threat_of_action": "سيتم اتخاذ الإجراءات القانونية المناسبة عند عدم السداد.",
    },
)

print(result.status)
print(result.plan.plan_summary)
print(result.answer_text)
```

You can also inspect the deterministic plan before execution:

```python
plan = client.agent.plan(
    goal="راجع سياسة الخصوصية الحالية وحدد الفجوات واقترح مسودة علاجية.",
    documents=[
        {
            "text": "توضح السياسة أغراض المعالجة دون آلية واضحة لطلبات أصحاب البيانات.",
            "document_type": "privacy_policy",
        }
    ],
    facts={
        "processing_context": "منصة رقمية",
        "generate_policy_draft": True,
        "company_name": "شركة ألف",
        "service_type": "منصة تقنية",
    },
)

for step in plan.steps:
    print(step.capability_id, step.status_hint, step.missing_inputs)
```

## 13. Common Faulty Scenarios

### Missing OpenAI key

```python
from qanuni import LegalClient

client = LegalClient()

client.drafting.improve(
    original_text="هذا نص يحتاج تحسينًا.",
    improvement_goals=["clarity"],
    context="contract",
)
```

Expected result:

- provider configuration error because no `OPENAI_API_KEY` was configured

### Mixed input styles

```python
client.drafting.improve(
    {"original_text": "نص أولي"},
    original_text="نص آخر",
    improvement_goals=["clarity"],
    context="memo",
)
```

Expected result:

- `QANUNI_VALIDATION_INPUT_CONFLICT`

### Missing contract source

```python
client.contracts.gap_analysis(contract_type="service_agreement")
```

Expected result:

- `QANUNI_VALIDATION_DOCUMENT_SOURCE_MISSING`

## 14. YAML Configuration

You can load the client from `.qanuni.yaml`:

```yaml
openai:
  api_key: "sk-..."
  model: "gpt-5-mini"

locale:
  language: "ar"
  jurisdiction: "SA"

performance:
  timeout: 60
  max_retries: 0

tools:
  drafting.improve:
    max_output_tokens: 1800
```

Then:

```python
from qanuni import LegalClient

client = LegalClient.from_config(".qanuni.yaml")
```

## 15. Full First Session Suggestion

If you are new to the SDK, use this order:

1. Install `qanuni-sdk` if you are testing the published package.
2. If you are still inside the repository before release, run `%pip install -e .` from `free_edition`.
3. Run `qanuni-examples --list`.
4. Run `qanuni-examples --category mocked_local`.
5. Add your `OPENAI_API_KEY` through `.env`.
6. Try `drafting.improve`.
7. Try `contracts.gap_analysis`.
8. Integrate the returned structured outputs into your app.

## 16. Maintainer Note

This free distribution is designed to keep the same PyPI project name `qanuni-sdk`, but it must be published as a **new version**, not by re-uploading the old one. See [docs/guides/README_PUBLISHING.md](docs/guides/README_PUBLISHING.md).

## 17. Expose Qanuni Through MCP

If you want another agentic client to use Qanuni through MCP instead of importing Python directly, serve the curated MCP layer:

```bash
qanuni-mcp-server serve --host 127.0.0.1 --port 8088
```

Default endpoints:

- health: `http://127.0.0.1:8088/healthz`
- MCP: `http://127.0.0.1:8088/mcp/`

The Phase-5 MCP surface is intentionally curated.

Exposed workflows:

- `workflow_contract_review`
- `workflow_pre_litigation_notice`

Exposed atomic tools:

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

Exposed resources:

- `qanuni://references/catalog`
- `qanuni://references/{packet_key}`
- `qanuni://runs`
- `qanuni://runs/{run_id}/output`
- `qanuni://runs/{run_id}/state`
- `qanuni://runs/{run_id}/findings`
- `qanuni://runs/{run_id}/artifacts/{artifact_name}`

This lets an external agent call one workflow, keep the returned `run_id`, inspect the workflow state later, and reuse generated artifacts such as a demand letter.

## 18. Run the Acceptance Pack

The free edition ships with a black-box acceptance pack so you can test the SDK
like a real external user before wider rollout.

List the available scenarios and packaged Arabic sample documents:

```bash
qanuni-acceptance --list
```

Run the full mocked acceptance pass without burning quota:

```bash
qanuni-acceptance --mode mocked
```

Run a focused scenario:

```bash
qanuni-acceptance --mode mocked --scenario atomic_extraction
qanuni-acceptance --mode mocked --scenario contract_review
qanuni-acceptance --mode mocked --scenario employment_review
```

Persist observability events into one working directory:

```bash
qanuni-acceptance --mode mocked --persist-observability --working-dir .qanuni_acceptance
```

If you installed the MCP extra, run the external MCP smoke test too:

```bash
qanuni-mcp-smoke --mode mocked --working-dir .qanuni_acceptance
```

The clean guided notebook for the same journey lives in [AcceptancePack.ipynb](AcceptancePack.ipynb), and the detailed checklist lives in [docs/guides/README_ACCEPTANCE.md](docs/guides/README_ACCEPTANCE.md).
