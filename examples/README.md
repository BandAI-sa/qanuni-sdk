# Human Testing Examples

This folder is a **manual human-testing suite** for the free edition.

Each file is intentionally verbose.
It is not trying to be minimal or elegant.
Its job is to let a human tester see:

- what input was used
- what surface was called
- what structured output came back
- what workflow or agent state was built
- what observability events were recorded
- what cache or MCP artifacts were written

## How to Run

From [E:/Private/Nawaf/BandAI_SDK/free_edition](/E:/Private/Nawaf/BandAI_SDK/free_edition):

```bash
python examples/example_00_environment_and_catalog.py
python examples/example_01_labor_deterministic.py
python examples/example_03_contract_review_workflow.py
```

Every script accepts:

```bash
--mode mocked
--mode live
--working-dir .qanuni_human_examples/example_name
--cli-verbosity simple
--output-file .qanuni_human_examples/example_name/report.json
--report-profile full
```

Default CLI behavior:

- `stdout` emits one final JSON report
- `stderr` shows live progress for the agent, workflows, and tool calls

Recommended when saving a real run:

```bash
python examples/example_12_legal_task_medium_commercial_claim.py --mode live --output-file hello2.json
```

This avoids PowerShell redirection encoding quirks and writes UTF-8 JSON directly.

## Report Profiles

The final JSON report now supports three shapes:

- `--report-profile full`
  Preserves the raw detailed report with every captured section. This is best
  for debugging, engineering review, and deep inspection of workflow state.
- `--report-profile compact`
  Keeps the run structured and traceable, but removes much of the bulky raw
  payload noise.
- `--report-profile legal`
  Produces a concise legal-facing brief that is easier to share with a lawyer
  or non-technical reviewer. It focuses on the legal question, what the agent
  did, key findings, recommended actions, and generated documents.

Recommended for legal review:

```bash
python examples/example_12_legal_task_medium_commercial_claim.py --mode live --report-profile legal --output-file hello2.json
```

Recommended for engineering/debug review:

```bash
python examples/example_12_legal_task_medium_commercial_claim.py --mode live --report-profile full --output-file hello2_full.json
```

Recommended baseline:

```bash
python examples/example_00_environment_and_catalog.py --mode mocked
python examples/example_02_atomic_legal_extraction.py --mode mocked
python examples/example_03_contract_review_workflow.py --mode mocked
python examples/example_06_agent_contract_dispute_notice.py --mode mocked
python examples/example_09_mcp_external_smoke.py --mode mocked
```

Use `mocked` first so you can validate the surface without burning quota.

## Agent Legal Task Scenarios

If your real goal is to evaluate the **legal agent itself** rather than the raw SDK surface,
start with the task scenarios below.

They are written as **legal missions** with increasing difficulty.
Each one is meant to answer a realistic Arabic legal question and let you observe:

- how the planner chooses the workflow path
- how the executor sequences approved capabilities
- how workflow state accumulates findings and recommendations
- how the final Arabic answer is synthesized
- how the agent behaves when information is missing

Dedicated reference:

- [LEGAL_TASKS.md](./LEGAL_TASKS.md)
- [LEGAL_TASK_ASSETS.md](./LEGAL_TASK_ASSETS.md)

## Files

### `example_00_environment_and_catalog.py`

Purpose:
- verifies package version and import path
- shows artifact paths
- lists packaged sample documents
- lists shipped tools and agent capabilities

Acceptance criteria:
- imports `qanuni` successfully
- prints the actual import path
- prints the packaged sample documents
- prints the tool catalog and agent capability list

### `example_01_labor_deterministic.py`

Purpose:
- tests deterministic labor tools without OpenAI
- shows fully structured outputs for labor surfaces

Acceptance criteria:
- `labor.end_of_service` returns a structured result
- `labor.probation_check` returns a structured result
- observability events are emitted

### `example_02_atomic_legal_extraction.py`

Purpose:
- tests the atomic legal building blocks on a service agreement
- shows classification plus extraction outputs in full detail

Acceptance criteria:
- classification succeeds
- clauses, parties, dates, amounts, obligations, termination terms, and dispute terms all return structured payloads
- observability records each call

### `example_03_contract_review_workflow.py`

Purpose:
- demonstrates one full orchestrated contract review
- shows workflow state, steps, findings, and recommendations

Acceptance criteria:
- workflow completes successfully
- step summaries are printed
- final structured workflow payload is visible
- observability events are visible

### `example_04_employment_review_workflow.py`

Purpose:
- demonstrates a full employment-review workflow
- combines atomic extraction with labor-law checks

Acceptance criteria:
- workflow completes successfully
- probation and end-of-service logic are reflected in the output
- workflow state is visible end to end

### `example_05_privacy_compliance_workflow.py`

Purpose:
- demonstrates PDPL-oriented review plus policy generation
- shows how the workflow compares the original text and the generated policy draft

Acceptance criteria:
- workflow completes successfully
- compliance score and remediation priorities are visible
- generated policy text is present

### `example_06_agent_contract_dispute_notice.py`

Purpose:
- demonstrates the planner and executor of the legal agent
- shows the deterministic plan and the final Arabic answer

Acceptance criteria:
- agent planning succeeds
- agent execution succeeds
- plan steps and final answer are both visible
- agent state includes completed capabilities and generated artifacts

### `example_07_cache_and_observability.py`

Purpose:
- demonstrates cache reuse on a repeated review-style tool call
- shows both in-memory events and persisted logs

Acceptance criteria:
- first call is a cache miss
- second call is a cache hit
- cache files are written
- observability log file is written

### `example_08_faulty_inputs_and_error_codes.py`

Purpose:
- demonstrates expected failures across tool, workflow, and agent layers
- shows `error_code`, message, and details explicitly

Acceptance criteria:
- the script catches structured `QanuniError` failures
- at least one tool error, one workflow error, and one agent error are shown
- the script exits successfully after printing them

### `example_09_mcp_external_smoke.py`

Purpose:
- demonstrates the curated MCP surface from the outside
- verifies that an external agentic client could use the shipped MCP server

Requirements:
- optional MCP dependencies installed

Acceptance criteria:
- temporary MCP server starts
- curated tool names are listed
- contract-review and pre-litigation surfaces both succeed
- MCP audit and observability artifacts are written

### `example_10_full_acceptance_report.py`

Purpose:
- runs the shipped acceptance scenarios as one consolidated report
- useful when a tester wants one command for a broad sanity pass

Acceptance criteria:
- full acceptance report returns successfully
- artifact paths are printed
- scenario outputs are present

### `example_11_legal_task_easy_contract_review.py`

Purpose:
- tests the agent on an easy contract-review mission
- useful when you want to watch one clean scenario with a single workflow only

Acceptance criteria:
- the planner selects `workflow.contract_review` only
- the answer explains the contract weaknesses in Arabic
- workflow breakdown shows classification, extraction, and risk-analysis stages

### `example_12_legal_task_medium_commercial_claim.py`

Purpose:
- tests a commercial claim scenario from contract review to pre-litigation notice
- shows how two workflows cooperate in one agent run

Acceptance criteria:
- the planner selects `workflow.contract_review` then `workflow.pre_litigation_notice`
- the final answer reflects both contract analysis and the demand path
- the state shows two completed capabilities or an equivalent two-step flow

### `example_13_legal_task_medium_employment_rights.py`

Purpose:
- tests an employment-rights mission with probation and end-of-service considerations
- useful for seeing legal reasoning in a labor context

Acceptance criteria:
- the planner selects `workflow.employment_review`
- the final answer explains labor risks and likely financial entitlements
- the workflow payload includes employment risks and follow-up recommendations

### `example_14_legal_task_hard_privacy_remediation.py`

Purpose:
- tests a PDPL-oriented remediation mission
- shows how the agent turns a weak privacy notice into a remediation plan

Acceptance criteria:
- the planner selects `workflow.privacy_compliance_review`
- the result exposes compliance gaps and remediation priorities
- a policy-draft path appears when sufficient generation context is supplied

### `example_15_legal_task_hard_policy_creation_review.py`

Purpose:
- tests policy generation plus review as one agent mission
- useful when you want to see generation and critique together

Acceptance criteria:
- the planner selects `workflow.policy_generation_review`
- the result includes generated text and review notes
- the final Arabic answer summarizes what was generated and what still needs attention

### `example_16_legal_task_complex_missing_info_recovery.py`

Purpose:
- tests the stopping rules and guardrails explicitly
- shows one failed/incomplete pass followed by a successful pass after the missing facts are supplied

Acceptance criteria:
- the first pass surfaces missing inputs or a next question
- the second pass completes successfully after supplementation
- the difference between the two passes is visible in both `answer_text` and `state`

## Suggested Human Test Order

1. `example_00_environment_and_catalog.py`
2. `example_01_labor_deterministic.py`
3. `example_02_atomic_legal_extraction.py`
4. `example_03_contract_review_workflow.py`
5. `example_04_employment_review_workflow.py`
6. `example_05_privacy_compliance_workflow.py`
7. `example_06_agent_contract_dispute_notice.py`
8. `example_07_cache_and_observability.py`
9. `example_08_faulty_inputs_and_error_codes.py`
10. `example_09_mcp_external_smoke.py`
11. `example_10_full_acceptance_report.py`

## Suggested Agent Legal-Task Order

1. `example_11_legal_task_easy_contract_review.py`
2. `example_12_legal_task_medium_commercial_claim.py`
3. `example_13_legal_task_medium_employment_rights.py`
4. `example_14_legal_task_hard_privacy_remediation.py`
5. `example_15_legal_task_hard_policy_creation_review.py`
6. `example_16_legal_task_complex_missing_info_recovery.py`

## Live Mode

When you want real provider execution, export a valid `OPENAI_API_KEY` and rerun with:

```bash
python examples/example_03_contract_review_workflow.py --mode live
python examples/example_05_privacy_compliance_workflow.py --mode live
python examples/example_06_agent_contract_dispute_notice.py --mode live
```

Start with a few scripts only in live mode, then expand after the mocked path is stable.
