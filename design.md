# Design: Dynamic Consultant Orchestration, Six-Pillar Blind-Spot Intake, And Expanded E2E Evals

## 1. Overview

The implementation will keep the existing FastAPI, LangGraph, and `SessionState` architecture while changing how the backend turns structured intake state into owner-facing language. `ProcessComponents` remains an internal working model; user-facing text must be synthesized from state rather than assembled by slot interpolation.

The new backend flow is:

```text
sanitize_input
  -> context_architect builds six-pillar coverage and one top blind spot across all pillars
  -> route_intent extracts or corrects internal process state
  -> route_intent asks one LLM-synthesized blind-spot question or natural playback
  -> user confirms
  -> execute_tools / synthesize_report
  -> synthesize_report incorporates six-pillar context
```

The design deliberately avoids new services or schema-breaking API changes. Metadata gains lightweight keys that are safe to persist and safe for downstream prompt construction.

The six pillars are a decision lens, not six separate intake queues. Each intake turn should evaluate all pillars and choose one top blind spot overall. The system must not ask one question per pillar.

## 2. Files

Primary implementation file:

```text
apps/api/app/core/orchestrator.py
```

Primary test and eval files:

```text
apps/api/tests/test_interview.py
apps/api/tests/test_analyst_behavior.py
apps/api/tests/test_orchestrator.py
apps/api/tests/test_resilience.py
apps/api/tests/evals/eval_dataset.py
apps/api/tests/evals/judge.py
apps/api/tests/evals/test_runner.py
apps/api/evals/golden_dataset.json
apps/api/evals/judge_prompts.py
apps/api/evals/test_agent_quality.py
```

Change ledger update for Phase 3:

```text
docs/DEFECT_LEDGER.md
```

No frontend files are expected to change.

## 3. Metadata Shape

`state.metadata` will carry the new planning data. The values are intentionally plain dictionaries so `SessionState` compatibility is preserved.

```json
{
  "architect_plan": {
    "business_vertical": "GENERIC",
    "requires_location": false,
    "required_components": ["trigger", "actor", "activity", "system"],
    "known_context": {
      "company_name": null,
      "company_industry": null,
      "company_core_tools": null
    },
    "six_pillar_coverage": {
      "market": {"status": "missing", "evidence": [], "open_question": "Who makes or influences the buying decision?"},
      "operations": {"status": "partial", "evidence": ["orders arrive on WhatsApp"], "open_question": null},
      "financials": {"status": "missing", "evidence": [], "open_question": "What does one delay or mistake cost?"},
      "personnel": {"status": "partial", "evidence": ["shop staff handle orders"], "open_question": null},
      "technology": {"status": "partial", "evidence": ["WhatsApp"], "open_question": null},
      "risk": {"status": "missing", "evidence": [], "open_question": "What would be the worst consequence of a missed order?"}
    },
    "selected_blind_spot": {
      "pillar": "market",
      "reason": "The user described the workflow but not who decides or influences demand.",
      "question": "Who decides what gets ordered: the customer, your staff, or someone else?"
    },
    "next_node": "route_intent"
  },
  "pending_intake_correction": "No, customers vote, not drivers"
}
```

Allowed coverage statuses:

```text
missing
partial
covered
```

The six-pillar metadata is not a required-user-input checklist. It is a consulting lens used to pick the next highest-value question and to ground final synthesis.

Only one selected blind spot should be stored per turn. If multiple pillars are weak, the selector must rank them and persist the single highest-leverage item in `selected_blind_spot`.

## 4. Context Architect Design

`_node_context_architect` will remain a non-speaking node, but it will gain a deterministic six-pillar coverage builder.

### 4.1 Pillar Definitions

Add a module-level constant:

```text
SIX_PILLARS
```

Each pillar includes a name, description, and keyword hints:

- Market: customers, demand, competitors, channels, pricing pressure.
- Operations: workflow steps, handoffs, throughput, delays, rework.
- Financials: revenue model, costs, margins, payback, cash constraints.
- Personnel: roles, ownership, staffing, training, incentives.
- Technology: tools, data flow, integrations, automation readiness.
- Risk: compliance, reliability, privacy, safety, fraud, dependency risks.

### 4.2 Coverage Helper

Add a helper:

```text
build_six_pillar_coverage(user_prompt, components, company_context) -> dict[str, dict[str, Any]]
```

The helper will:

1. Inspect latest user text, accumulated `process_components`, company industry, and core tools.
2. Mark each pillar as `covered`, `partial`, or `missing`.
3. Store short evidence snippets without adding raw payloads.
4. Produce a candidate open question for missing or partial pillars.

This first version may be deterministic. If an LLM is available later in the turn, the question-generation prompt receives the coverage and can phrase the final question naturally.

### 4.3 Blind Spot Helper

Add a helper:

```text
select_blind_spot(six_pillar_coverage, components, architect_plan) -> dict[str, str]
```

Selection priority:

1. Pick a pillar whose absence can materially change the recommendation.
2. Prefer decision-critical gaps over rigid slot order.
3. Keep operations/process basics high enough priority to preserve current intake behavior when the workflow itself is unclear.
4. Never select a blind spot whose question would require multiple answers.
5. Select exactly one top blind spot across all six pillars, not one blind spot per pillar.

Example priority by context:

- If no workflow trigger exists, Operations can remain the selected blind spot.
- If workflow steps are present but customers or decision-makers are absent, Market or Personnel can be selected.
- If a process has financial constraints but no cost/volume signal, Financials can be selected.
- If sensitive data, payments, health, safety, or compliance terms appear, Risk can be selected.

### 4.4 Architect Plan Update

`_node_context_architect` will continue to set:

```text
business_vertical
requires_location
required_components
known_context
next_node
```

It will additionally set:

```text
six_pillar_coverage
selected_blind_spot
```

The existing dynamic location requirement remains unchanged.

## 5. Route Intent Design

`_node_route_intent` remains responsible for extraction, correction handling, confirmation gating, and user-facing intake messages.

### 5.1 Sentinel Policy

Internal sentinels such as `"UNKNOWN"` must never be copied directly into assistant messages.

Add helpers:

```text
is_missing_component_value(value) -> bool
sanitize_components_for_prompt(components) -> dict[str, Optional[str]]
```

`is_missing_component_value` treats `None`, empty strings, `"UNKNOWN"`, `"VARIABLE"`, `"null"`, and `"Not specified"` as missing for user-facing generation.

`sanitize_components_for_prompt` converts those values to `None` before sending context to prompts.

### 5.2 Dynamic Question Prompt

Replace the current "ask about one missing component" prompt with a consultant prompt that accepts both:

```text
selected_missing_item
selected_blind_spot
six_pillar_coverage
```

The prompt must instruct the LLM to:

1. Acknowledge one concrete thing the owner said.
2. Ask exactly one short question.
3. Use the selected blind spot when it is more decision-critical than the next missing process slot.
4. Avoid internal labels and schema terms.
5. Avoid placeholder words.
6. Avoid asking for bottlenecks or pain points directly.
7. Treat structured state as grounding only, not as copy to echo.

Fallback behavior:

- If no LLM is available, use `selected_blind_spot.question` when present.
- If no blind-spot question exists, use the existing missing-component fallback.
- Wrap deterministic fallback with `build_thread_pulling_acknowledgement`, but only after removing placeholder tokens from the acknowledgement context.

### 5.3 Dynamic Playback Prompt

Add a new prompt constant and helper:

```text
CONSULTANT_PLAYBACK_PROMPT
build_consultant_playback_message(...)
```

Inputs:

- latest user message,
- conversation history,
- sanitized components,
- company context,
- architect plan,
- six-pillar coverage,
- selected blind spot,
- pending correction context,
- target language.

Prompt rules:

1. Summarize only known, concrete details.
2. Do not mention missing fields or placeholder tokens.
3. Do not use JSON, field labels, or schema words.
4. If a previous assistant assumption was corrected, the newest user correction wins.
5. Ask the user to confirm or correct the updated understanding.
6. Do not ask a separate blind-spot question inside playback; confirmation is the single ask for that turn.

Fallback behavior:

- Use a helper such as `build_known_details_playback`.
- Build a sentence from known facts only.
- If only one known fact exists, acknowledge that fact and ask the user to confirm or correct.
- Never render `UNKNOWN`, `None`, `null`, `Not specified`, `Trigger:`, `Actor:`, `Activity:`, `System:`, or `Friction:`.

### 5.4 Escape-Hatch Behavior

The existing escape hatch can keep filling missing internal values with `"UNKNOWN"` for schema compatibility if needed, but user-facing generation must always use sanitized components.

Updated behavior:

```text
user says "I don't know" or clarification_turns >= 2
  -> missing internal fields may become UNKNOWN
  -> sanitized prompt context converts UNKNOWN to null
  -> playback message describes known facts only
  -> no UNKNOWN appears in assistant text
```

## 6. Correction Routing Design

The confirmation classifier prompt will be expanded from a narrow confirmation/correction detector to an overwrite-aware update classifier.

### 6.1 Classifier Contract

The classifier still returns JSON, but the schema will include correction confidence and notes:

```json
{
  "is_confirmation": false,
  "corrections": {
    "trigger": null,
    "actor": "customers",
    "activity": null,
    "system": null,
    "friction": null,
    "location": null
  },
  "unmapped_correction": null
}
```

Prompt rule:

```text
Newer user statements override older accumulated components and assistant summaries.
```

### 6.2 Application Rules

1. If `is_confirmation` is true and there are no corrections, set `playback_confirmed = True`.
2. If any correction value is present, overwrite the matching `components` key and keep `playback_confirmed = False`.
3. If `unmapped_correction` is present, store it in `metadata.pending_intake_correction` and keep `playback_confirmed = False`.
4. Re-run completeness checks after applying corrections.
5. Generate a fresh playback message from sanitized state.

### 6.3 Offline Correction Fallback

When no LLM is available:

- Detect obvious negative correction starts such as `no`, `not`, `actually`, `rather`, `instead`.
- Store the full message in `metadata.pending_intake_correction`.
- Do not guess the target field unless a simple existing keyword match is clear.
- Keep `playback_confirmed = False`.

This preserves user intent without fabricating a structured overwrite.

## 7. Synthesis Design

`_node_synthesize_report` will receive the six-pillar metadata and selected blind spot in its prompt.

### 7.1 Live LLM Prompt Additions

Add instructions:

1. Evaluate recommendations against Market, Operations, Financials, Personnel, Technology, and Risk.
2. Use the blind spot as an explicit caveat if it remains unresolved.
3. Do not present assumptions as facts.
4. Continue the Zero-Jargon rule, recommendation hierarchy, user constraints, benchmark warnings, company context priority, and geographic guidance.

The JSON output shape remains unchanged.

### 7.2 Fallback Report

Replace the current slot dump fallback with a natural fallback builder:

```text
build_natural_fallback_report(components, architect_plan, selected_blind_spot) -> dict[str, str]
```

Behavior:

- `as_is_workflow`: summarize known details in prose.
- `friction_analysis`: explain that unresolved details limit confidence and name the likely area to inspect, not placeholder values.
- `technology_neutral_recommendations`: recommend observing one real workflow example, confirming ownership, and validating the selected blind spot.
- `roi_economics`: say that savings need volume/time/cost inputs before calculation.

The fallback must not emit `UNKNOWN`, rigid slot labels, or placeholder phrases.

## 8. State Flow

### 8.1 Incomplete Intake

```text
latest user message
  -> sanitize_input
  -> context_architect builds coverage and blind spot
  -> route_intent extracts components
  -> route_intent checks dynamic required components
  -> if incomplete, ask one blind-spot or missing-detail question
  -> status = AWAITING_CLARIFICATION
```

### 8.2 Playback Confirmation

```text
required components are present or escape hatch is reached
  -> sanitize components for prompt
  -> generate natural playback through LLM or fallback
  -> ask user to confirm or correct
  -> status = AWAITING_CLARIFICATION
```

### 8.3 Correction

```text
user correction
  -> confirmation classifier detects correction
  -> overwrite structured component or store pending correction
  -> regenerate playback from newest state
  -> playback_confirmed remains false
```

### 8.4 Confirmed Synthesis

```text
user confirms playback
  -> playback_confirmed = true
  -> planning/execution continues
  -> synthesize_report receives six-pillar metadata
  -> completed state stores backward-compatible report fields
```

## 9. Test Design

### 9.1 Update Existing Tests

`apps/api/tests/test_interview.py`:

- Replace assertions that assistant text contains `UNKNOWN` in escape-hatch tests.
- Assert internal components may retain `UNKNOWN` only if necessary, while assistant messages do not.
- Add a test for `No, customers vote, not drivers` overwriting actor or storing pending correction.
- Update synthesis prompt test to assert six-pillar rubric terms are present.

`apps/api/tests/test_analyst_behavior.py`:

- Add a case where the next question comes from a blind spot, not only missing process slot order.
- Continue asserting one natural question and no premature solution terms.

`apps/api/tests/test_resilience.py`:

- Update fallback synthesis expectations so no placeholder slot dump appears after LLM failure.

### 9.2 New Assertions

Use shared forbidden terms where practical:

```text
UNKNOWN
None
null
Not specified
Trigger:
Actor:
Activity:
System:
Friction:
```

Tests should distinguish between internal state and assistant-facing messages.

### 9.3 Eval Fixture Updates

Update `apps/api/tests/evals/eval_dataset.py` scenarios that currently contain or expect `UNKNOWN` prose. The fixtures may keep internal mock JSON values if needed, but final playback and synthesis examples must not reward placeholder text.

Update judge guidance to penalize:

- placeholder leakage,
- rigid slot playback,
- ignoring explicit corrections,
- asking multiple blind-spot questions.

### 9.4 Expanded Eval Architecture

The eval suite should have three layers so broad coverage does not make every local run slow or brittle:

```text
fast deterministic evals
  -> mocked LLM scenario replay
  -> optional live LLM-as-judge quality evals
```

#### 9.4.1 Fast Deterministic Evals

Fast evals should run in normal targeted validation and should not require network access or live API keys. They validate:

- state transitions,
- accumulated process components,
- `six_pillar_coverage` shape,
- exactly one `selected_blind_spot`,
- exactly one assistant question during intake,
- no user-facing placeholder leakage,
- correction overwrite behavior,
- fallback report JSON key compatibility,
- no retired `SUGGESTER` or `EVALUATOR` mode assumptions.

These checks should live primarily in `apps/api/tests/evals/test_runner.py` and adjacent deterministic test modules.

#### 9.4.2 Mocked LLM Scenario Replay

Mocked scenario replay should use fictional companies and deterministic mock responses to exercise the full orchestrator path without relying on live model variance.

The existing `EvalScenario` shape in `apps/api/tests/evals/eval_dataset.py` should be extended rather than replaced. Add optional fields such as:

```text
scenario_tags
expected_blind_spot_pillar
expected_blind_spot_reason_contains
expected_question_count
forbidden_assistant_terms
expected_judge_dimensions
privacy_sensitivity
adversarial_input
```

The mock Anthropic node matcher in `apps/api/tests/evals/test_runner.py` must recognize the current prompt vocabulary:

- sanitization,
- process mapping,
- intake confirmation classifier,
- plain-spoken operational consultant,
- consultant playback,
- report writer.

This keeps fixture failures understandable when prompt names change.

#### 9.4.3 Live LLM-As-Judge Evals

Live judge evals remain optional and should run only when an API key is present or when explicitly requested with the eval marker. The judge should score separate dimensions:

- routing and state correctness,
- consultant intake quality,
- single-blind-spot discipline,
- six-pillar reasoning,
- zero-jargon compliance,
- recommendation hierarchy,
- factual grounding,
- privacy and safety posture,
- correction handling.

The judge must penalize:

- rigid field-label summaries,
- multiple intake questions in one turn,
- hidden reintroduction of placeholder prose,
- unsupported metrics or invented facts,
- ignored user corrections,
- premature Gen AI recommendations,
- unsafe handling of private, payment, health, employee, or customer data.

### 9.5 Fictional Company Catalog

Add or expand scenarios so the suite covers at least these ten SMB archetypes:

1. Neighborhood clinic or healthcare practice.
2. Kirana, grocery, retail, or local store.
3. Repair shop or field-service business.
4. Wholesale distributor.
5. Small manufacturer.
6. Restaurant, cafe, or catering operator.
7. Logistics, dispatch, or delivery team.
8. Professional services firm.
9. Education or training center.
10. Real estate, brokerage, or property operations team.

Each company scenario should include enough operational texture to test real consultation behavior:

- company context,
- geography,
- staff roles,
- current systems,
- recurring workflow,
- user constraints,
- known ambiguity,
- privacy or compliance sensitivity when relevant,
- expected recommendation direction.

### 9.6 Scenario Pattern Matrix

The fictional catalog should be tagged so coverage can be audited without reading every fixture. Required tags:

```text
vague_start
rich_start
multi_turn
correction
contradiction
dont_know
escape_hatch
mixed_language
impatient_user
late_constraints
privacy_sensitive
prompt_injection
fallback_no_key
synthesis_success
synthesis_failure
tool_untrusted_output
```

Not every company needs every tag, but the whole suite must cover the full matrix.

### 9.7 Legacy Eval Migration

Existing evals must be audited before adding large new coverage. Migration rules:

1. Keep useful scenarios, but update expected playback and judge examples to the new consultant behavior.
2. Delete or rewrite cases whose only purpose was to reward placeholder output or rigid slot order.
3. Keep internal `UNKNOWN` sentinel values only where they test fallback compatibility.
4. Add assertions that internal sentinels never reach assistant messages or final reports.
5. Update judge prompts in both eval locations so old and new runners score the same product behavior.
6. Ensure every scenario uses `OPTIMIZER`; retired modes should fail fixture review.

### 9.8 Eval Failure Reporting

Eval failure messages should identify the failure class:

```text
STATE_TRANSITION
COMPONENT_ACCUMULATION
PILLAR_METADATA
BLIND_SPOT_SELECTION
ASSISTANT_TEXT_POLICY
CORRECTION_OVERWRITE
SYNTHESIS_SCHEMA
JUDGE_SCORE
MOCK_FIXTURE_DRIFT
```

This avoids the common failure mode where a semantic quality regression looks like a fixture mismatch, or a fixture drift looks like a product bug.

## 10. Validation

Phase 3 targeted validation:

```powershell
cd apps/api
pytest tests/test_interview.py tests/test_analyst_behavior.py tests/test_orchestrator.py tests/test_resilience.py -q
pytest tests/evals/test_runner.py -q
```

If prompt, synthesis, or routing behavior changes materially:

```powershell
cd apps/api
pytest evals/ -v --run-evals
```

For expanded eval work, also run the fastest deterministic subset before any source commit:

```powershell
cd apps/api
pytest tests/evals/test_runner.py -q
```

Run broader semantic judge coverage explicitly when API keys are available:

```powershell
cd apps/api
pytest evals/ tests/evals/ -v --run-evals
```

Executable-source commits must use the repository secure checkpoint path. Documentation-only changes remain eligible for `--no-verify` after confirming only documentation files are staged.

## 11. Risks And Mitigations

- Risk: Deterministic pillar coverage is less nuanced than live LLM reasoning.
  - Mitigation: Use deterministic coverage for stable metadata and let the LLM perform the natural phrasing when available.

- Risk: Blind-spot questions could disrupt basic intake completeness.
  - Mitigation: Keep Operations/process basics high priority when the workflow itself is not yet understandable.

- Risk: Correction classification can mis-map user intent.
  - Mitigation: Preserve unmapped corrections in metadata and ask for confirmation instead of forcing a guessed field.

- Risk: Existing eval fixtures expect old placeholder output.
  - Mitigation: Update tests and judge criteria in the same implementation phase.

- Risk: Removing placeholders from fallback output can hide uncertainty.
  - Mitigation: Express uncertainty in natural language, such as "I still need the person who owns this step before treating recommendations as final."
