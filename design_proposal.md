# Design Proposal: Management Consulting Discovery Evals

This proposal covers the requested evolution of the LangGraph orchestrator and E2E evaluation suite. It is design-only; no orchestrator or eval code should be changed until this plan is approved.

## Objective

BuildSense should behave like a careful operations consultant during intake. When the user says something vague like “Billing is a mess,” the graph should not behave like a form filler, ask for internal schema labels, or jump to recommendations. It should empathize, identify what is missing, ask one plain-language question at a time, and only synthesize a solution after enough business/process facts have been confirmed.

## Current State

The graph now includes:

```text
sanitize_input -> context_architect -> route_intent -> await_human / execute_tools -> synthesize_report
```

Relevant current behavior:

- `context_architect` creates `metadata.architect_plan` and can require `location` for physical businesses.
- `route_intent` still owns most interview behavior, including extraction, confirmation, escape hatch handling, and question generation.
- The question-generation prompt already bans some machine labels and forbids asking directly for “bottlenecks,” but it does not yet consistently prioritize the three consulting discovery dimensions:
  - hand-offs,
  - volume/frequency,
  - quantified friction.
- The E2E eval dataset is structured for multi-turn mocked LLM responses, but its assertions focus mostly on status and `process_components`, not question quality or final ROI defaulting.

## Proposed Behavior

For vague complaints, the intake flow should follow a “Management Consulting Discovery” ladder.

1. Acknowledge the problem in human terms.
2. Identify the process area without pretending to know the workflow.
3. Ask for hand-offs first: who sends work to whom, and where the information moves.
4. Ask for volume/frequency next: how often it happens per day/week/month.
5. Ask for quantified friction next: rough time lost, rework, error count, or delay.
6. Confirm the understood workflow naturally.
7. Only after confirmation, execute tools and synthesize tiered recommendations.

The graph should still honor the existing `clarification_turns >= 2` escape hatch. When the turn limit is reached, it should stop interrogating and proceed with explicit `UNKNOWN` or defaulted assumptions, clearly framed in the final report as assumptions.

## Orchestrator Changes

### 1. Expand Architect Plan

Add a `discovery_plan` section inside `metadata.architect_plan`.

Proposed shape:

```json
{
  "business_vertical": "GENERIC",
  "requires_location": false,
  "required_components": ["trigger", "actor", "activity", "system"],
  "discovery_plan": {
    "is_vague_complaint": true,
    "process_area": "billing",
    "priority_dimensions": ["handoffs", "volume_frequency", "quantified_friction"],
    "collected_dimensions": {
      "handoffs": false,
      "volume_frequency": false,
      "quantified_friction": false
    },
    "next_dimension": "handoffs"
  }
}
```

Detection heuristics:

- Vague complaint examples: “billing is a mess,” “dispatch is slow,” “things get delayed,” “invoices are painful,” “orders are chaotic.”
- If there is a complaint but no clear actors/systems/volume/time loss, mark `is_vague_complaint=true`.
- If the user supplies concrete actors and systems in the first turn, skip directly to the missing dimension.

### 2. Add Discovery Dimensions To State

Use metadata for low-risk implementation first:

```python
metadata["discovery_context"] = {
    "handoffs": Optional[str],
    "volume_frequency": Optional[str],
    "quantified_friction": Optional[str],
    "labor_rate_assumption": Optional[dict],
}
```

Do not add new Pydantic fields until this shape stabilizes. The final report can consume `metadata.discovery_context`.

### 3. Update Extraction Prompt

Update the `extract_process_components` prompt to extract the extra dimensions in addition to existing process components:

```json
{
  "trigger": "...",
  "actor": "...",
  "activity": "...",
  "system": "...",
  "friction": "...",
  "location": "...",
  "handoffs": "...",
  "volume_frequency": "...",
  "quantified_friction": "...",
  "hourly_wage": null
}
```

Extraction rules:

- `handoffs`: who sends/receives work and which systems or artifacts carry it.
- `volume_frequency`: count per day/week/month or qualitative frequency if no count is available.
- `quantified_friction`: hours lost, delay time, error rate, rework count, or “not provided.”
- `hourly_wage`: only if explicitly provided by the user.

### 4. Update Clarification Question Prompt

Replace the current generic “missing component” question prompt with dimension-aware question generation.

Prompt requirements:

- Ask one question only.
- Use everyday language.
- Strictly forbid these words during discovery:
  - bottleneck
  - throughput
  - SOP
  - workflow optimization
  - ROI
  - leverage
  - automation architecture
  - CAC
  - LTV
- Do not ask “what is the friction?” Instead ask concrete variants:
  - “Where does the work wait?”
  - “How many of these happen in a normal week?”
  - “About how much time does someone lose each time?”
  - “Who gets the request first, and where do they pass it next?”

Question priority:

1. If `handoffs` missing: ask who receives/sends the work and what tools/artifacts each side uses.
2. Else if `volume_frequency` missing: ask how many times it happens in a typical day/week/month.
3. Else if `quantified_friction` missing: ask for a rough time loss, delay, rework, or error estimate.
4. Else if required process component missing: ask for the missing component in plain language.
5. Else present natural confirmation.

### 5. Escape Hatch Behavior

Keep the current `clarification_turns >= 2` limit, but change the fallback response strategy:

- Fill missing process fields with `UNKNOWN`.
- Fill missing discovery fields with `UNKNOWN`.
- Set `metadata["assumptions_needed"] = True`.
- Continue to confirmation rather than asking more.

Final synthesis must explicitly say where assumptions were used.

### 6. Dynamic ROI Economics Defaulting

Add a small deterministic helper in the synthesizer path:

```python
derive_labor_rate_assumption(
    role: str | None,
    business_vertical: str | None,
    location: str | None,
    company_industry: str | None,
) -> dict
```

Initial default table:

```python
WAREHOUSE_OR_DISPATCH = {
    "hourly_rate": 250,
    "currency": "INR",
    "basis": "default local operations staff assumption"
}

ACCOUNTING_OR_ADMIN = {
    "hourly_rate": 350,
    "currency": "INR",
    "basis": "default local bookkeeping/admin assumption"
}

GENERIC_SMB_STAFF = {
    "hourly_rate": 300,
    "currency": "INR",
    "basis": "default small business staff assumption"
}
```

Rules:

- If user provides wage, use user-provided wage.
- Else infer from role/process:
  - warehouse, picker, dispatcher, driver, packing staff -> warehouse/dispatch default.
  - accountant, bookkeeper, admin, invoicing clerk -> accounting/admin default.
  - otherwise -> generic SMB staff default.
- Store the chosen default in `metadata.discovery_context.labor_rate_assumption`.
- Synthesis prompt must state that this is an assumption and can be adjusted.

Synthesis prompt addition:

> If hourly wage is missing, use the provided labor-rate assumption from metadata. Present it clearly as an assumption, not a fact. Calculate simple ROI from frequency × time lost × assumed hourly labor cost. If volume or time loss is unknown, provide a conservative scenario range and label it as a rough planning estimate.

## E2E Evaluation Changes

### Dataset Schema Updates

Extend `Turn` in `apps/api/tests/evals/eval_dataset.py`:

```python
class Turn(TypedDict):
    user_input: str
    expected_status: str
    expected_components: Dict[str, Any]
    expected_discovery: NotRequired[Dict[str, Any]]
    expected_question_contains: NotRequired[List[str]]
    forbidden_question_terms: NotRequired[List[str]]
    expected_metadata: NotRequired[Dict[str, Any]]
    mock_llm_responses: List[MockLLMCall]
    clarification_turns: Optional[int]
```

Update `test_runner.py` to assert:

- `expected_discovery` against `state.metadata["discovery_context"]`.
- `expected_question_contains` against latest assistant message or latest clarification question.
- `forbidden_question_terms` are absent from the latest user-facing question.
- `expected_metadata` for labor-rate assumptions and architect plan flags.

Also update playback capture. It currently looks for old emoji/schema strings. It should capture messages containing:

- `If that sounds right`
- `from what you've shared`
- or the latest assistant message before confirmation.

### Scenario A: Physical Operations

Name:

`Consulting Discovery - Warehouse Dispatch Delays`

Purpose:

Validate vague physical-operations discovery with hand-offs, volume/frequency, quantified friction, completion, and tiered recommendations.

Turn outline:

1. User: `Dispatch is always delayed. Sales says warehouse is the problem.`
   - Expected: `AWAITING_CLARIFICATION`
   - Expected question should ask about hand-offs.
   - Required wording should include something like `who gets the order first` or `where does it go next`.
   - Forbidden terms: `bottleneck`, `throughput`, `SOP`, `optimization`, `ROI`.
   - Mock extractor returns only broad area/friction, no complete components.

2. User: `Sales emails orders to a shared inbox. Warehouse supervisor reads email, writes jobs on a whiteboard, then tells pickers from memory.`
   - Expected components:
     - trigger: sales order email received
     - actor: warehouse supervisor and pickers
     - activity: write jobs on whiteboard and verbally assign picking
     - system: shared email inbox, whiteboard, memory
   - Expected discovery:
     - handoffs: sales email -> warehouse supervisor -> whiteboard -> pickers
   - Expected question asks volume/frequency.

3. User: `Maybe 35 orders a day, more on Mondays.`
   - Expected discovery:
     - volume_frequency: 35 orders/day, higher Mondays
   - Expected question asks for rough time lost/errors.

4. User: `About 2 hours a day are lost checking status, and maybe 5 orders a week get picked late.`
   - Expected discovery:
     - quantified_friction: 2 hours/day and 5 late picks/week
   - Expected: `AWAITING_CLARIFICATION`
   - Expected confirmation message, not solution.

5. User: `Yes, correct.`
   - Expected: `COMPLETED`
   - Mock synthesis includes:
     - Tier 1: whiteboard cutoff/check-in routine
     - Tier 2: shared order tracker or Kanban board
     - Tier 3: not recommended unless unstructured email parsing is unavoidable
     - ROI: uses warehouse/dispatch labor default if wage not provided.

### Scenario B: Financial Operations

Name:

`Consulting Discovery - Field Technician Invoicing Delays`

Purpose:

Validate financial/admin workflow discovery with multiple systems, WhatsApp image hand-off, volume/frequency, quantified friction, and accounting labor default.

Turn outline:

1. User: `Invoicing takes forever and customers keep chasing us.`
   - Expected: `AWAITING_CLARIFICATION`
   - Expected question asks where the job details come from and who receives them.
   - Forbidden terms: `bottleneck`, `throughput`, `SOP`, `ROI`, `automation architecture`.

2. User: `Field technicians send WhatsApp photos of job cards to the office. Admin types them into Excel and then again into Zoho Books.`
   - Expected components:
     - trigger: technician sends job card photo
     - actor: field technicians and office admin
     - activity: type job-card details into Excel and Zoho Books
     - system: WhatsApp, Excel, Zoho Books
   - Expected discovery:
     - handoffs: technician WhatsApp photo -> admin -> Excel -> Zoho Books
   - Expected question asks volume/frequency.

3. User: `Around 60 job cards a week.`
   - Expected discovery:
     - volume_frequency: 60 job cards/week
   - Expected question asks time lost or error/rework estimate.

4. User: `Each one takes 8 minutes to type, and 10 percent need corrections because photos are unclear.`
   - Expected discovery:
     - quantified_friction: 8 minutes/card and 10 percent correction rate
   - Expected confirmation.

5. User: `Yes, that's right.`
   - Expected: `COMPLETED`
   - Mock synthesis includes:
     - Tier 1: photo quality/job-card checklist
     - Tier 2: form capture or Zoho intake form
     - Tier 3: OCR/AI only if photo variability remains high
     - ROI: uses accounting/admin labor default if wage not provided.

## Test Runner Assertion Design

Add helper functions:

```python
def latest_assistant_text(state: SessionState) -> str: ...
def assert_contains_all(text: str, snippets: list[str]) -> None: ...
def assert_contains_none(text: str, forbidden_terms: list[str]) -> None: ...
def assert_nested_metadata(state: SessionState, expected: dict) -> None: ...
```

For deterministic LLM mocking, update `make_mock_anthropic()` so it can map the new prompt type:

- `management consulting discovery`
- `discovery question`
- `labor-rate assumption`

If we keep this inside existing extractor/question prompts, no new node classifier is needed. If we introduce a separate prompt purpose later, use `MockLLMCall.node = "discovery_question_generator"`.

## Expected Prompt Adjustments

### Question Generator Prompt

Add a section:

```text
MANAGEMENT CONSULTING DISCOVERY MODE
When the user gives a vague operational complaint, do not ask for labels. Ask one practical question that uncovers the next missing dimension:
1. hand-offs: who receives the work, who passes it next, and what tool or artifact carries it
2. volume/frequency: how many times per day/week/month
3. quantified friction: rough time lost, delay, rework, or error count

Use everyday language. Do not use: bottleneck, throughput, SOP, ROI, optimization, architecture, leverage.
```

### Extractor Prompt

Add fields:

```json
"handoffs": "who passes work to whom and through what tools/artifacts, or null",
"volume_frequency": "how often this happens, or null",
"quantified_friction": "rough time lost, delay, error rate, or rework count, or null",
"hourly_wage": "explicit wage only, or null"
```

### Synthesis Prompt

Add:

```text
ROI DEFAULTING RULE
If the user did not provide hourly wages, use metadata.discovery_context.labor_rate_assumption. State clearly that it is an assumption. If volume and time loss are available, calculate estimated weekly/monthly cost. If either is missing, show a conservative range and ask the user to validate it before financial decisions.
```

## Risks And Mitigations

- Risk: More required discovery dimensions can make users feel interrogated.
  - Mitigation: Keep one-question turns and preserve escape hatch.
- Risk: Default labor rates may appear too authoritative.
  - Mitigation: Always label them as planning assumptions.
- Risk: E2E mocked evals may pass while live LLM wording drifts.
  - Mitigation: Add deterministic forbidden-term assertions and later add LLM-judge rubrics specifically for discovery tone.
- Risk: Existing evals expect old playback/schema formatting.
  - Mitigation: Update playback capture logic and judge rubrics to prefer conversational confirmation.

## Implementation Order After Approval

1. Add discovery metadata helpers and labor-rate default helper.
2. Update extractor and question-generation prompts.
3. Update synthesis prompt to use default labor assumptions.
4. Extend `eval_dataset.py` schema with question/metadata assertions.
5. Add Scenario A and Scenario B fixtures.
6. Update `test_runner.py` assertions.
7. Run:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m pytest tests/evals -v
.\.venv\Scripts\python.exe -m pytest tests/test_analyst_behavior.py tests/test_interview.py tests/test_ontology.py tests/test_langgraph.py -v
.\.venv\Scripts\python.exe -m mypy app
```

8. Fix failures until all discovery and synthesis behavior matches the approved contract.
