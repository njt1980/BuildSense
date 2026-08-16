# Design: Iterative Discovery Orchestrator And Ambiguity Fallback

## 1. Overview

The implementation will keep the existing FastAPI, Pydantic `SessionState`, and LangGraph `StateGraph` structure. The change is concentrated in the backend orchestrator intake path so BuildSense can run a bounded discovery conversation before synthesis.

The current graph already contains the right major nodes:

```text
sanitize_input
  -> context_architect
  -> route_intent
  -> await_human or execute_tools
  -> synthesize_report
```

Phase 3 will refine those nodes rather than adding a parallel orchestration engine. The new flow is:

```text
sanitize_input
  -> context_architect updates discovery metadata and next-turn strategy
  -> route_intent extracts explicit workflow facts
  -> route_intent emits Handshake, Neutral Gap, or Multiple Choice Anchor
  -> await_human until the user responds
  -> repeat discovery while confidence is low and turns < 3
  -> synthesize_report when confidence is high or turn 3 dead-ends
```

The design preserves Optimizer-only mode, budget caps, untrusted-tool wrapping, context pruning, existing report metadata keys, and the flexible `metadata` dictionary contract.

## 2. Files

Primary executable implementation:

```text
apps/api/app/core/orchestrator.py
```

Primary tests:

```text
apps/api/tests/test_interview.py
apps/api/tests/test_orchestrator.py
apps/api/tests/test_analyst_behavior.py
apps/api/tests/test_resilience.py
```

Potential eval fixture updates if prompt behavior changes materially:

```text
apps/api/evals/golden_dataset.json
apps/api/evals/test_agent_quality.py
apps/api/evals/judge_prompts.py
apps/api/tests/evals/eval_dataset.py
apps/api/tests/evals/test_runner.py
```

Required change-ledger update during Phase 3:

```text
docs/DEFECT_LEDGER.md
```

No frontend changes are expected.

## 3. Constants And Metadata

Add or standardize these module-level constants in `orchestrator.py`:

```text
MAX_CLARIFICATION_TURNS = 3
E2E_CONFIDENCE_THRESHOLD = 0.72
LOW_CONFIDENCE_THRESHOLD = 0.5
```

The existing `clarification_turns` field remains the durable turn counter. Additional discovery state will live in `state.metadata["iterative_discovery"]`:

```json
{
  "turn_index": 2,
  "max_turns": 3,
  "e2e_confidence_score": 0.42,
  "confidence_reasons": [
    "contract intake channel is known",
    "approval ownership is not mapped",
    "signed-versus-pending separation is inconsistent"
  ],
  "known_workflow_facts": [
    "vendor contracts arrive by email",
    "the owner flags some emails",
    "counter-signing PDFs can be missed"
  ],
  "open_workflow_gaps": [
    "no stable owner or approval state is known",
    "no central contract register is confirmed"
  ],
  "latest_answer_quality": "dead_end",
  "next_question_strategy": "ambiguity_fallback",
  "should_synthesize_now": true,
  "ambiguity_fallback": true
}
```

Allowed `latest_answer_quality` values:

```text
specific
vague
dead_end
unknown
confirmation
correction
```

Allowed `next_question_strategy` values:

```text
handshake
neutral_gap
multiple_choice_anchor
playback
ambiguity_fallback
```

This metadata is intentionally plain JSON-compatible data so `SessionState.metadata` needs no schema-breaking model change.

## 4. Helper Functions

Add focused helpers in `orchestrator.py`.

### 4.1 Discovery Turn Classification

```text
classify_answer_quality(user_prompt: str, components: dict[str, Any]) -> str
```

Responsibilities:

1. Detect vague answers such as "we just email them," "I figure it out," or "try to remember."
2. Detect dead-end answers such as "depends on the day" or "whatever works."
3. Detect unknown answers already handled by the current escape-hatch keywords.
4. Return a conservative quality label for routing and prompt strategy.

### 4.2 Workflow Fact Extraction For Confidence

```text
build_known_workflow_facts(messages: list[Any], components: dict[str, Any]) -> list[str]
build_open_workflow_gaps(components: dict[str, Any], answer_quality: str) -> list[str]
```

These helpers must produce short, non-sensitive summaries from current state only. They must not store raw tool outputs or large transcripts.

### 4.3 E2E Confidence Score

```text
calculate_e2e_confidence_score(
    components: dict[str, Any],
    answer_quality: str,
    architect_plan: dict[str, Any],
) -> tuple[float, list[str]]
```

Scoring design:

1. Award baseline confidence for known trigger, actor, activity, system, and optional location.
2. Award confidence for stable handoff/approval signals in the conversation.
3. Penalize vague, unknown, or dead-end latest answers.
4. Penalize placeholder values such as `UNKNOWN`.
5. Keep friction optional; the user's original bleeding-neck statement often already expresses it.

The score is not a business-quality score. It only decides whether the as-is workflow is mapped enough to produce safe recommendations.

### 4.4 Discovery Metadata Builder

```text
build_iterative_discovery_metadata(
    state: AgentState,
    components: dict[str, Any],
    architect_plan: dict[str, Any],
    answer_quality: str,
) -> dict[str, Any]
```

This helper calculates confidence, known facts, open gaps, and the next prompt strategy. It also sets:

```text
should_synthesize_now = confidence >= E2E_CONFIDENCE_THRESHOLD or clarification_turns >= MAX_CLARIFICATION_TURNS
ambiguity_fallback = clarification_turns >= MAX_CLARIFICATION_TURNS and confidence < LOW_CONFIDENCE_THRESHOLD
```

## 5. Context Architect Design

`_node_context_architect` remains a non-speaking planning node.

Phase 3 changes:

1. Keep existing vertical, location, six-pillar, and selected-blind-spot metadata.
2. Add iterative-discovery planning metadata before returning.
3. Choose prompt strategy based on turn and answer quality:
   - turn 0: `handshake`,
   - later turn with vague input: `multiple_choice_anchor`,
   - later turn with specific but incomplete input: `neutral_gap`,
   - turn cap reached with low confidence: `ambiguity_fallback`.
4. Keep domain mirroring hints in metadata, derived from company context and user vocabulary.

Suggested metadata addition:

```json
{
  "domain_mirror_terms": {
    "business_object": "vendor contracts",
    "failure_event": "vendor did not show up",
    "workflow_name": "contract approval flow"
  }
}
```

The architect must not send user-facing text directly. It prepares the strategy consumed by `_node_route_intent`.

## 6. Route Intent Design

`_node_route_intent` remains responsible for extraction, confirmation handling, and user-facing intake messages.

### 6.1 Extraction

Keep the current extraction contract for:

```text
trigger
actor
activity
system
friction
location
```

The extraction prompt must stay conservative:

1. Extract only explicit user statements.
2. Do not invent software, approval owners, folders, spreadsheets, or CRMs.
3. Treat newer corrections as overriding older assumptions.

### 6.2 Turn Cap

Replace hardcoded `clarification_turns >= 2` escape-hatch checks with `clarification_turns >= MAX_CLARIFICATION_TURNS`.

Do not fill missing fields with `UNKNOWN` solely because turn 2 was reached. Turn 3 should route to synthesis with ambiguity metadata instead of forcing fake completeness.

### 6.3 User-Facing Discovery Prompt

Replace or extend `CONSULTANT_INTAKE_PROMPT` so it accepts:

```text
next_question_strategy
iterative_discovery_json
domain_mirror_terms_json
selected_blind_spot_json
components_json
history
latest_user_message
```

Prompt rules by strategy:

1. `handshake`: validate pain, promise to help, ask permission to inspect the broader workflow.
2. `neutral_gap`: anchor on a known fact and ask one open-ended "How" or "What" question.
3. `multiple_choice_anchor`: acknowledge the vague answer, then offer two or three relatable options in one question.
4. `playback`: summarize known concrete facts and ask for confirmation or correction.

Universal rules:

1. Ask exactly one question.
2. Avoid leading yes/no questions.
3. Avoid internal schema labels.
4. Do not assume tools or roles the user did not mention.
5. Mirror domain vocabulary.
6. Focus only on the immediate bleeding-neck workflow.

### 6.4 Deterministic Fallback Questions

Add fallback builders for the core strategies:

```text
build_handshake_fallback(user_prompt: str, domain_terms: dict[str, str]) -> str
build_neutral_gap_fallback(components: dict[str, Any], domain_terms: dict[str, str]) -> str
build_multiple_choice_anchor_fallback(components: dict[str, Any], domain_terms: dict[str, str]) -> str
```

For the Starlight Events path, deterministic fallback should be capable of producing safe variants of:

```text
How do you currently separate the emails with signed contracts from the ones you still need to review?
```

and:

```text
When you flag them, do you eventually move them to a specific folder, log them in a spreadsheet, or just leave them in the main inbox?
```

Fallbacks can be generic for unknown domains but must remain non-leading and must not claim an option as fact.

### 6.5 Routing Out Of Intake

The `_route_after_intent` conditional should gain a synthesis route or equivalent metadata path. The cleanest design is:

```text
route_intent returns status = SYNTHESIZING when should_synthesize_now is true
_route_after_intent maps SYNTHESIZING -> synthesize_report
```

This requires extending the existing conditional mapping from:

```text
await_human
execute_tools
```

to:

```text
await_human
execute_tools
synthesize_report
```

If the existing code instead proceeds through `execute_tools` for all confirmed workflows, that path should be preserved for high-confidence confirmed workflows. Low-confidence ambiguity fallback should skip tool execution and go directly to `synthesize_report` because tool research would amplify unverified assumptions.

## 7. Synthesis Design

`_node_synthesize_report` must read:

```text
metadata["iterative_discovery"]
metadata["architect_plan"]
process_components
conversation history
```

### 7.1 Normal Synthesis

When `ambiguity_fallback` is false:

1. Solve the immediate bleeding-neck issue first.
2. Keep the existing backward-compatible metadata keys:
   - `as_is_workflow`,
   - `friction_analysis`,
   - `technology_neutral_recommendations`,
   - `roi_economics`.
3. Add or include a `next_horizons` metadata key if the UI can tolerate additional metadata.
4. If adding a new key is risky, append a `Next Horizons` paragraph to `technology_neutral_recommendations`.

### 7.2 Ambiguity Fallback Synthesis

When `ambiguity_fallback` is true:

1. The prompt must state that the workflow remains highly custom, inconsistent, or reliant on personal intuition.
2. It must include an explicit `Unverified Assumptions` block.
3. It must list missing data from `open_workflow_gaps`.
4. It must forbid specific software recommendations.
5. It must recommend process principles first.
6. It must include a Next Horizons hook that is clearly sequenced after the first process standardization step.

For Starlight Events, the target report direction is:

```text
Unverified Assumptions:
Because we have not mapped a standardized contract flow, this strategy assumes there is currently no central database such as a spreadsheet or CRM being used.

Recommendation:
Create one strict contract intake channel, such as contracts@starlight.com, and use it only for vendor contracts before paying for contract management software.

Next Horizons:
Once the dedicated contract inbox is stable, automate signatures with e-sign templates.
```

### 7.3 Deterministic Fallback Report

Extend `build_natural_fallback_report` or add:

```text
build_ambiguity_fallback_report(
    components: dict[str, Any],
    iterative_discovery: dict[str, Any],
    domain_terms: dict[str, str],
) -> dict[str, str]
```

The fallback report must:

1. Avoid `UNKNOWN`, `None`, `null`, `Not specified`, and schema labels in user-facing text.
2. Include `Unverified Assumptions` in low-confidence turn-three state.
3. Avoid software recommendations in low-confidence turn-three state.
4. Keep the legacy report keys populated.

## 8. Test Design

### 8.1 Unit Tests For Helpers

Add focused tests in `apps/api/tests/test_interview.py` or a new backend test module:

1. `classify_answer_quality` detects vague and dead-end answers.
2. `calculate_e2e_confidence_score` increases with mapped trigger/actor/activity/system.
3. Low-confidence dead-end state sets `ambiguity_fallback = true` at turn 3.
4. `MAX_CLARIFICATION_TURNS` is 3.

### 8.2 Golden Scenario 4 Orchestrator Test

Add a deterministic or mocked-LLM test that replays:

```text
User: I keep losing track of vendor contracts...
Assistant: Handshake
User: We just email them.
Assistant: Neutral Gap
User: I just flag them...
Assistant: Multiple Choice Anchor
User: It really depends...
Assistant/State: routes to synthesize_report, no fourth question
```

Assertions:

1. First response validates pain and asks to inspect the broader approval flow.
2. Second response asks a "How" or "What" question about signed versus pending contracts.
3. Third response offers two or three options without claiming any as fact.
4. After the dead-end answer, `metadata.iterative_discovery.ambiguity_fallback` is true.
5. No fourth clarification question is appended.
6. Report includes `Unverified Assumptions`.
7. Report recommends a dedicated contract inbox or equivalent communication-channel standardization.
8. Report does not mention Zapier, CRM, contract management software as an immediate recommendation, or other specific software.
9. Report includes `Next Horizons`.

### 8.3 Existing Test Updates

Update tests that encode the old two-turn escape hatch:

1. `test_escape_hatch_max_turns` should use `MAX_CLARIFICATION_TURNS` rather than `2`.
2. Tests should expect synthesis or ambiguity fallback at turn 3, not forced `UNKNOWN` playback.
3. Existing placeholder leakage assertions remain valuable and should stay.

### 8.4 Synthesis And Resilience Tests

Update `apps/api/tests/test_resilience.py` so LLM failure in ambiguity fallback still produces:

1. backward-compatible report keys,
2. `Unverified Assumptions`,
3. no placeholder leakage,
4. no immediate specific software recommendation.

## 9. Validation

Phase 3 targeted validation:

```powershell
cd apps/api
pytest tests/test_interview.py tests/test_orchestrator.py tests/test_analyst_behavior.py tests/test_resilience.py -q
```

If eval fixtures or judge prompts are changed:

```powershell
cd apps/api
pytest tests/evals/test_runner.py -q
pytest evals/ -v --run-evals
```

Before any executable-source commit, follow the secure checkpoint process required by the repository. Documentation-only checkpoint commits remain eligible for `--no-verify` after verifying only documentation files are staged.

## 10. Risks And Mitigations

- Risk: The scoring helper may overfit to current component fields.
  - Mitigation: Treat the score as routing confidence only and preserve open gaps in metadata for synthesis.

- Risk: Multiple Choice Anchor questions could become leading.
  - Mitigation: The prompt and fallback builder must phrase options as possibilities, not facts.

- Risk: Routing directly to synthesis may bypass useful tool research.
  - Mitigation: Only low-confidence ambiguity fallback skips tools; high-confidence confirmed workflows can keep the existing execution path.

- Risk: Tests may become brittle if they assert exact LLM wording.
  - Mitigation: Assert strategy, question count, forbidden terms, and required concepts rather than full transcript text.

- Risk: The final report shape may not have a dedicated `next_horizons` UI field.
  - Mitigation: Store `next_horizons` in metadata when safe and also include a clearly labeled section in existing recommendation text.
