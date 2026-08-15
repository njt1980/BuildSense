# Specification: Dynamic Consultant Orchestration And Six-Pillar Blind-Spot Intake

## 1. Problem

The backend orchestration loop can produce robotic placeholder dialogue such as `UNKNOWN UNKNOWN when UNKNOWN` when required intake fields are missing or when the escape-hatch path fills missing process components with sentinel values. This happens because parts of the orchestration path construct owner-facing dialogue with rigid templates and direct `ProcessComponents` slot interpolation instead of asking the LLM to synthesize natural language from the current state.

The current orchestration prompts also focus too narrowly on workflow slots and bottleneck deduction. BuildSense needs to behave like a dynamic, outside-the-box business consultant that can reason laterally across the user's whole business, identify what the user has not mentioned, and ask one high-leverage question rather than forcing the conversation through a fixed state progression.

## 2. Goals

1. Remove user-facing `UNKNOWN` placeholder dialogue from intake playback and report fallback paths.
2. Stop injecting rigid user-facing template sentences from extracted Pydantic process slots.
3. Pass extracted state, conversation history, company context, and missing-field context back to the LLM for natural response synthesis whenever an API key is available.
4. Update the `context_architect` or equivalent intake/synthesis prompt path to evaluate user input across six pillars: Market, Operations, Financials, Personnel, Technology, and Risk.
5. Instruct the LLM to identify the biggest blind spot based on what the user has not said across the six pillars, then ask exactly one targeted question about that blind spot.
6. Ensure user corrections overwrite previous assumptions instead of being treated as failed confirmations or forced into a rigid progression.
7. Preserve Optimizer-only mode, budget caps, untrusted-tool XML boundaries, context pruning, tenant isolation, and existing API contracts.

## 3. Non-Goals

1. Do not introduce LangGraph alternatives, external agent frameworks, or new orchestration services.
2. Do not change frontend UI structure unless backend response shape requires a compatibility fix.
3. Do not reintroduce `SUGGESTER` or `EVALUATOR` modes.
4. Do not remove the existing `ProcessComponents` schema; it remains internal state, not user-facing copy.
5. Do not ask multiple blind-spot questions in a single turn.
6. Do not make recommendations before the intake confirmation gate is satisfied.

## 4. Current Suspected Implementation Surface

The implementation is expected to focus on `apps/api/app/core/orchestrator.py`:

1. `_node_context_architect`
   - Currently builds a deterministic internal intake plan from latest user text, company context, physical-business heuristics, and required process components.
   - Must gain six-pillar analysis instructions and metadata output describing pillar coverage and the selected blind spot.

2. `_node_route_intent`
   - Currently extracts and merges `trigger`, `actor`, `activity`, `system`, `friction`, and `location`.
   - Contains the playback confirmation path that formats owner-facing text with component slot values: `actor_phrase activity_phrase when trigger_phrase, using system_phrase`.
   - Contains escape-hatch logic that writes `"UNKNOWN"` into missing fields after declined answers or clarification turn exhaustion.
   - Must stop exposing those sentinel values in user-facing messages and must route correction text into overwrite behavior.

3. `CONSULTANT_INTAKE_PROMPT` and any playback-generation prompt
   - Must be updated so the LLM receives structured state as grounding only and produces natural owner-facing language without internal labels, schema terms, or placeholder tokens.
   - Must ask one targeted blind-spot question when intake is incomplete.

4. `_node_synthesize_report`
   - Currently uses a live LLM prompt for report JSON, but the fallback report generator still emits slot labels and `UNKNOWN` values.
   - Must be made safe for no-key or LLM-error environments by producing natural, non-placeholder fallback language.

5. Tests and eval fixtures
   - Existing tests intentionally assert `UNKNOWN` in some escape-hatch messages. Those tests must be updated to assert the new behavior.
   - Golden eval fixtures containing `UNKNOWN`-driven outputs must be revised so they do not reward placeholder dialogue.

## 5. Functional Requirements

### 5.1 Dynamic Natural Playback

- When all required intake fields are present, the confirmation playback must be synthesized as natural conversational language.
- The LLM prompt must receive:
  - latest user message,
  - relevant conversation history,
  - accumulated process components,
  - company context,
  - architect plan,
  - six-pillar coverage summary,
  - explicit correction context when present.
- The user-facing playback must not contain `UNKNOWN`, `None`, `null`, `Not specified`, internal schema labels, JSON, or field names such as `Trigger`, `Actor`, `Activity`, `System`, or `Friction`.
- The playback must still ask the user to confirm or correct the summary before analysis proceeds.
- If the LLM call is unavailable, the deterministic fallback must omit unknown details instead of verbalizing sentinel placeholders.

### 5.2 Six-Pillar Rubric

- The `context_architect` or equivalent synthesis/intake planning node must evaluate the conversation across:
  - Market: customers, demand, competitors, channels, pricing pressure.
  - Operations: workflow steps, handoffs, throughput, delays, rework.
  - Financials: revenue model, costs, margins, payback, cash constraints.
  - Personnel: roles, ownership, staffing, training, incentives.
  - Technology: tools, data flow, integrations, automation readiness.
  - Risk: compliance, reliability, privacy, safety, fraud, dependency risks.
- The node must store a lightweight pillar coverage summary in `metadata` for downstream prompts and tests.
- The rubric must be used to reason about what matters next; it must not require the user to answer all six pillars before the system can progress.

### 5.3 Blind Spot Directive

- The architect prompt must identify the biggest blind spot from what the user has not said, not only from missing workflow slots.
- The blind spot must be selected for expected decision value, not simply first missing field order.
- The next user-facing question must ask about exactly one blind spot.
- The question must be short, specific, and grounded in the user's business context.
- The question must avoid generic prompts such as "What are your pain points?" or "What bottlenecks do you have?"
- The question must not present unconfirmed assumptions as facts.

### 5.4 Correction Routing And Assumption Overwrites

- When the latest user message corrects a prior assumption, such as "No, customers vote, not drivers", the confirmation classifier must:
  - detect that the message is a correction rather than a confirmation,
  - identify the corrected field or assumption,
  - overwrite the previous value in `process_components` or the relevant metadata,
  - preserve the correction in conversation history,
  - keep `playback_confirmed` false until the updated playback is confirmed.
- Correction prompts must explicitly instruct the LLM that newer user statements override older assistant summaries and previous extracted values.
- If the correction cannot be mapped to a known field, it must be stored as pending correction context and passed into the next LLM playback/question prompt instead of being discarded or forced into `system`.

### 5.5 Placeholder And Sentinel Handling

- `UNKNOWN` may remain as an internal sentinel only if needed for compatibility with existing schemas or eval setup.
- User-facing text must never include `UNKNOWN UNKNOWN`, `when UNKNOWN`, or visible placeholder values from missing fields.
- Missing values should be represented to the LLM as structured absence, for example `null` in prompt context, and the LLM must be instructed to speak around absent details naturally.
- Deterministic fallback copy must say what is known and ask for the next useful clarification without listing unknown slots.

### 5.6 Report Synthesis

- The synthesis prompt must continue to enforce:
  - Zero-Jargon rule,
  - recommendation hierarchy,
  - user constraints,
  - benchmark-data warnings,
  - company context priority,
  - geographic enrichment when present.
- The synthesis prompt must additionally incorporate the six-pillar rubric and blind-spot analysis.
- Final report JSON keys must remain backward compatible:
  - `as_is_workflow`,
  - `friction_analysis`,
  - `technology_neutral_recommendations`,
  - `roi_economics`.
- Any fallback report path must avoid placeholder slot dumps and instead produce cautious, natural language based only on confirmed known information.

## 6. Acceptance Criteria

1. A session with missing fields that previously produced `UNKNOWN UNKNOWN when UNKNOWN` now produces natural confirmation or clarification text with no visible placeholder tokens.
2. Escape-hatch scenarios caused by "I don't know" or clarification turn exhaustion do not display `UNKNOWN` in assistant messages.
3. The `context_architect` prompt or metadata includes the six pillars: Market, Operations, Financials, Personnel, Technology, and Risk.
4. The next clarification question is selected from the biggest blind spot across the six pillars and asks exactly one targeted question.
5. A correction such as "No, customers vote, not drivers" overwrites the previous actor/decision-maker assumption and regenerates playback for confirmation.
6. New or updated backend tests cover:
   - no user-facing `UNKNOWN` placeholders,
   - six-pillar prompt/metadata presence,
   - blind-spot single-question behavior,
   - correction overwrite routing,
   - synthesis fallback without placeholder slot dumps.
7. Relevant eval fixtures no longer expect or reward `UNKNOWN` placeholder prose.
8. Targeted backend tests pass for orchestrator intake, analyst behavior, and synthesis fallback.
9. If executable source changes later fail a checkpoint, the defect is logged in `docs/DEFECT_LEDGER.md` before retrying, per repository instructions.

## 7. Validation Plan For Phase 3

Phase 3 implementation should run targeted validation first:

```powershell
cd apps/api
pytest tests/test_interview.py tests/test_analyst_behavior.py tests/test_orchestrator.py tests/test_resilience.py -q
pytest tests/evals/test_runner.py -q
```

If prompt, synthesis, or orchestrator routing behavior changes materially, run:

```powershell
cd apps/api
pytest evals/ -v --run-evals
```

Before any executable-source commit, use the repository's secure checkpoint process and ensure no secrets, `.env`, runtime logs, caches, virtual environments, or unrelated files are staged.

## 8. Risks And Constraints

- Existing tests and eval fixtures encode old placeholder behavior, so they must be updated alongside the implementation.
- The no-key deterministic fallback cannot be as creative as the live LLM path, but it must still avoid leaking internal sentinel values.
- Six-pillar reasoning should improve consultant quality without turning every intake into a long interrogation.
- Correction routing must avoid overfitting to exact phrases and should rely on LLM classification when available, with conservative metadata preservation when unavailable.
- Prompt changes may affect LLM-as-judge scores, so eval updates must distinguish desired consultant behavior from looser, less grounded recommendations.
