# Specification: Iterative Discovery Orchestrator And Ambiguity Fallback

## 1. Problem

BuildSense currently moves too quickly from a user's first pain statement into synthesis. That behavior can produce recommendations before the system understands the end-to-end workflow behind the user's immediate "bleeding neck" problem.

For complex SMB workflows, the agent must behave like a consultative operator: validate the pain, ask permission to inspect the broader flow, then iteratively discover the current process without leading the owner toward a predetermined tool. When the owner cannot describe a stable process after a bounded number of turns, the final report must avoid hallucinated workflow details and recommend foundational process principles instead of software.

## 2. Goals

1. Upgrade the backend LangGraph orchestration flow to support iterative discovery across a maximum of three clarification turns.
2. Add an internal `MAX_CLARIFICATION_TURNS = 3` policy for the iterative discovery loop.
3. Add an `e2e_confidence_score` check that estimates whether the as-is workflow is sufficiently mapped for synthesis.
4. Route incomplete low-confidence workflows back to `context_architect` while turns remain below the maximum.
5. Route to `synthesize_report` when confidence is high enough or when the three-turn cap is reached.
6. Update the `context_architect` prompt so the first assistant turn uses a Consultative Handshake.
7. Update subsequent discovery turns so they use Neutral Gap questions instead of leading yes/no questions.
8. Support a Multiple Choice Anchor when the user provides vague, low-information answers.
9. Update report synthesis so low-confidence turn-three reports use an Ambiguity Fallback.
10. Ensure final reports solve the immediate bleeding-neck issue first, then include a Next Horizons hook for one intentionally deferred adjacent business pillar.

## 3. Non-Goals

1. Do not introduce a new orchestration framework or replace LangGraph.
2. Do not reintroduce `SUGGESTER` or `EVALUATOR` modes.
3. Do not expand discovery into a general business audit before addressing the user's immediate issue.
4. Do not add frontend UI changes unless an existing backend response contract would otherwise break.
5. Do not recommend software during low-confidence ambiguity fallback reports.
6. Do not ask more than one owner-facing clarification question in a single assistant turn.

## 4. Functional Requirements

### 4.1 Iterative Discovery Loop

- The graph routing logic must support iterative discovery through `context_architect` up to `MAX_CLARIFICATION_TURNS = 3`.
- Each discovery cycle must update lightweight workflow completeness metadata, including:
  - `clarification_turns`,
  - `e2e_confidence_score`,
  - known workflow facts,
  - missing or ambiguous workflow gaps,
  - whether the latest user answer was vague or dead-ended.
- If `e2e_confidence_score` is below the synthesis threshold and `clarification_turns < MAX_CLARIFICATION_TURNS`, route back to `context_architect`.
- If `e2e_confidence_score` is sufficient, route to `synthesize_report`.
- If `clarification_turns >= MAX_CLARIFICATION_TURNS`, route to `synthesize_report` even when confidence remains low, with ambiguity metadata preserved.

### 4.2 Consultative Handshake

- On the first discovery turn, BuildSense must:
  - validate the user's pain in plain language,
  - promise to help with the immediate bleeding-neck issue,
  - ask permission to inspect the broader workflow that produces the pain.
- The handshake must not prematurely recommend tools, vendors, integrations, or implementation details.
- The handshake must mirror the user's domain vocabulary, such as "vendor contracts" for event planning, "patients" for clinics, or "mats" for yoga studios.

### 4.3 Neutral Gap Questions

- After the handshake, BuildSense must anchor on a known fact from the user's answer and ask an open-ended "How" or "What" question.
- Neutral Gap questions must not ask leading yes/no questions.
- Neutral Gap questions must not assume unmentioned tools, folders, spreadsheets, CRMs, staff roles, automations, or software.
- The question must focus on mapping the end-to-end workflow connected to the immediate bleeding-neck problem.

### 4.4 Multiple Choice Anchor

- If the user's answer is vague, low-information, or relies on phrases such as "we just email them," "I figure it out," "it depends," or "whatever works," the next discovery turn may offer two or three concrete examples.
- The examples must lower cognitive load without treating any option as fact.
- The assistant should still ask one question only.
- Example shape: "When you flag them, do you move them to a folder, log them in a spreadsheet, or leave them in the main inbox?"

### 4.5 Ambiguity Fallback

- When `clarification_turns >= MAX_CLARIFICATION_TURNS` and `e2e_confidence_score` remains low, synthesis must pivot tone.
- The report must frame the workflow as highly custom, inconsistent, or reliant on personal intuition.
- The report must not invent missing workflow steps, owners, databases, tools, or approval rules.
- The report must include an explicit `Unverified Assumptions` block that states what is missing from discovery.
- Recommendations must be principle-based and process-first.
- Specific software recommendations, including CRMs, Zapier-style automation, or contract-management platforms, are forbidden in this fallback state.

### 4.6 Iceberg Delivery And Next Horizons

- Final reports must address the immediate bleeding-neck problem first.
- Reports may mention adjacent business pillars only after the immediate issue has a practical first step.
- Reports must include a `Next Horizons` section that names one adjacent improvement area intentionally left for later.
- The Next Horizons hook must be specific to the workflow discovered, such as e-signature templates after contract inbox standardization.

## 5. Golden Scenario 4 Acceptance Behavior

Scenario: Starlight Events loses vendor contracts in email. The florist failed to show up because a PDF was not counter-signed.

Expected conversation pattern:

1. User says they lose vendor contracts in a chaotic inbox.
2. BuildSense uses the Handshake: acknowledges that a missing vendor on event day is stressful, promises to organize the contract flow, and asks to inspect how a vendor gets approved from start to finish.
3. User says, "We just email them."
4. BuildSense uses a Neutral Gap: asks how signed contracts are separated from items still needing review.
5. User says they flag emails or try to remember.
6. BuildSense uses a Multiple Choice Anchor: asks whether flagged contracts move to a folder, spreadsheet, or stay in the inbox.
7. User says it depends on the day and they do whatever works.
8. Because the third discovery turn has dead-ended, BuildSense routes to synthesis.
9. The report states an unverified assumption that no standardized contract flow or central database has been mapped.
10. The report recommends standardizing the communication channel first, such as using a dedicated contracts inbox, before paying for contract management software.
11. The report includes a Next Horizons hook about automating signatures with e-sign templates after the dedicated contract inbox is stable.

## 6. Broader Golden Transcript Coverage

The prompts and routing must also naturally support:

1. Retail to Wholesale: midnight wholesale texts lead to discovery of notepad-to-whiteboard double entry and a Google Form to Google Sheet intake recommendation, with ingredient procurement as the Next Horizon.
2. Field Services: paper work orders in vans lead to discovery of dispatch-to-invoice delay and a mobile parts form recommendation, with van inventory restocking as the Next Horizon.
3. Service and Wellness: yoga no-shows lead to discovery that the owner personally manages cancellations by text, with cancellation policy and auto-waitlist configuration as the recommendation, and client retention as the Next Horizon.

## 7. Acceptance Criteria

1. The backend exposes or stores `MAX_CLARIFICATION_TURNS = 3` for iterative discovery.
2. Routing loops to `context_architect` for incomplete low-confidence workflows while under the turn cap.
3. Routing proceeds to `synthesize_report` when confidence is high or the turn cap is reached.
4. The first discovery assistant response follows the Consultative Handshake pattern.
5. Subsequent discovery responses follow Neutral Gap rules and avoid leading yes/no questions.
6. Vague answers trigger a Multiple Choice Anchor with two or three relatable options.
7. Scenario 4 reaches synthesis after the ambiguous third answer without asking a fourth discovery question.
8. Low-confidence turn-three reports include `Unverified Assumptions`.
9. Low-confidence turn-three reports recommend process principles and do not recommend specific software.
10. Final reports include a bleeding-neck-first recommendation and a Next Horizons hook.
11. Tests cover the Scenario 4 ambiguity fallback path.
12. Existing Optimizer-only, budget cap, untrusted-tool wrapping, context pruning, and backward-compatible report-shape behavior remain intact.

## 8. Validation Plan For Phase 3

Targeted backend validation should include:

```powershell
cd apps/api
pytest tests/test_interview.py tests/test_orchestrator.py tests/test_analyst_behavior.py tests/test_resilience.py -q
```

If prompt or synthesis behavior changes materially, run the eval suite:

```powershell
cd apps/api
pytest evals/ -v --run-evals
```

Before executable-source commits, use the repository secure checkpoint process and ensure no secrets, runtime files, caches, virtual environments, or unrelated files are staged.

## 9. Risks And Constraints

- LLM wording may vary, so deterministic tests should assert policy and routing behavior rather than exact full transcripts.
- The Multiple Choice Anchor must avoid becoming a leading recommendation in disguise.
- The ambiguity fallback must be useful without pretending the workflow was fully mapped.
- Iterative discovery must remain bounded so impatient owners still receive a practical report quickly.
- The existing six-pillar consultant metadata can inform Next Horizons, but the discovery loop must stay focused on the immediate bleeding-neck problem.

---

# Specification Addendum: Evaluation Harness, Dashboard, and Quality Enhancements (Phase 4)

## 1. Problem Statement

While BuildSense has a comprehensive set of E2E evaluation scenarios, the verification pipeline suffers from two distinct gaps:
1. **Mock Execution Limitation**: The 22 E2E scenarios mock the Anthropic Claude API responses during the state machine's execution turns. This means we verify state-machine transitions and metadata mapping, but we do not verify the actual quality, tone, or compliance of the active LLM prompts when running live.
2. **Lack of Visual Observability**: Running evaluations from the command line only outputs simple pass/fail logs. It is difficult for a developer to trace step-by-step turn inputs, parsed components, confidence scores, and individual judge rubric scores without manually parsing raw terminal trace outputs.
3. **Untested Quality Constraints**: Business rules—such as the Zero-Jargon rule requiring parenthesized analogies on *every single occurrence* of jargon (not just the first)—and strict constraint compliance (e.g., "Strict Data Privacy" or "No Budget") are not deterministically tested.

## 2. Goals

1. **E2E Live Execution Flag**: Add a command-line parameter `--live` to the test runner so E2E scenarios can execute live (un-mocked) Anthropic API calls for all nodes when desired.
2. **Configurable Model Settings**: Allow developers to select model configurations (e.g. using `claude-haiku-4-5-20251001` or `claude-sonnet-5`) to control API cost vs grading accuracy during live evaluations.
3. **Deterministic Quality Unit Tests**:
   - Write unit tests verifying that the Zero-Jargon rule is strictly followed on repeated terms (e.g., LTV, CAC, ROI).
   - Write integration tests verifying that constraints (e.g., "Strict Data Privacy", "No Budget") dynamically restrict or shape recommendation tiers.
4. **Evaluation Results Exporter**: Build a custom exporter in `conftest.py` that serializes detailed evaluation traces, latencies, cost, and LLM judge scores to `apps/api/evals/eval_results.json` after running the suite.
5. **Dev Evaluations Endpoint**: Expose `GET /api/dev/evaluations/results` in FastAPI to serve the serialized E2E execution log.
6. **Evaluations Dashboard**: Design a developer dashboard page in Next.js at `/dev/evaluations` to visualize pass/fail rates, execution statistics, step-by-step turn dialogues, and LLM judge scorecard ratings.

## 3. Non-Goals

1. Do not replace `pytest`. All evaluations should still run via standard pytest triggers.
2. Do not expose the evaluations dev routes or dashboard in production environments.
3. Do not run live E2E evals by default to avoid accidental token billing; live runs must require the explicit `--live` flag.

## 4. Functional Requirements

### 4.1 CLI & Execution Harness
- Extend [`conftest.py`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/conftest.py) to accept the `--live` flag.
- When `--live` is specified:
  - Bypasses the mock Anthropic client in [`test_runner.py`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/tests/evals/test_runner.py) and connects to the active Anthropic model API.
  - Allows model configuration overrides (e.g., defaulting to Claude 3.5 Haiku to minimize live evaluation run costs).
- Capture execution metrics for every run:
  - Turn latency (seconds) and cumulative scenario duration.
  - Calculated input/output token usage and USD costs using standard Anthropic pricing.

### 4.2 Quality Enhancement Assertions
- **Jargon Analogy Leakage Test**: Write a unit test that verifies that any occurrence of a jargon term (LTV, CAC, ROI, MRR, SaaS, Webhook, API, DB) in synthesized reports is followed by parenthesized analogies on *all* occurrences, failing if a repeat occurrence is unparenthesized.
- **Constraint Compliance Verification**: Write unit tests asserting that:
  - Under `No Budget` / `Low Budget` constraints, the recommendation tier avoids paid SaaS licenses or custom cloud software.
  - Under `Strict Data Privacy` constraints, cloud webhook integrations or SaaS platforms that process sensitive details are warned against or skipped.

### 4.3 Evaluations Exporter
- Capture the step-by-step history of each scenario:
  - User turn input.
  - Assistant playback, neutral gap, or clarification question.
  - Extracted `process_components` (trigger, actor, activity, system, friction, location).
  - Calculated `e2e_confidence_score` and chosen `next_question_strategy`.
- Capture LLM-as-a-judge scorecards:
  - `zero_jargon_score`, `hierarchy_integrity_score`, `consultant_intake_score`, `single_blind_spot_score`, `factual_grounding_score`, and `privacy_safety_score`.
- Serialize results to `apps/api/evals/eval_results.json` upon completion of the test suite.

### 4.4 FastAPI Dev Route
- Expose `GET /api/dev/evaluations/results`.
- Return the parsed contents of `eval_results.json`.
- Gate the route to local development mode only:
  - `settings.environment == "local"` and `settings.local_telemetry_viewer_enabled == True`.

### 4.5 Next.js Evaluations Dashboard
- Accessible at `/en/dev/evaluations` (and general `/dev/evaluations` route).
- **KPI Summary Cards**:
  - Overall Pass Rate (%)
  - Total Cost ($)
  - Average Latency (s)
  - Execution Type (Mock vs. Live)
- **Scenario Timeline & Details**:
  - Render a filterable list of all scenarios (All, Passed, Failed).
  - Expandable case detail section showing the step-by-step conversation bubbles (matching user inputs and assistant responses).
  - Comparative view of expected vs. actual process components.
  - Visualization of the 6 LLM judge scorecards.

## 5. Acceptance Criteria

1. Running `pytest tests/evals --run-evals` runs successfully in mock mode.
2. Running `pytest tests/evals --run-evals --live` executes un-mocked runs with the live Anthropic API and LLM Judge.
3. Tests fail if jargon repeat occurrences are unparenthesized or constraints are violated.
4. An `eval_results.json` file is correctly written to `apps/api/evals/` containing the E2E case traces.
5. The `GET /api/dev/evaluations/results` API returns the JSON log.
6. The Next.js `/dev/evaluations` page renders the KPI summaries, case lists, turn traces, and judge metrics accurately.

---

# Specification Addendum: Behavioral Prompt Patching (Phase 5)

## 1. Problem Statement

Our recent LLM-as-a-judge evaluation run passed structurally, but identified three behavioral regressions in the LangGraph prompt outputs:
1. **Internal Metadata Leakage (The Fourth Wall Rule):** Exposing internal LangGraph state variables or framework labels directly to the user instead of translating state logic into natural English.
2. **Premature Summarization (The Discovery vs. Confirmation Boundary):** Asking closed confirmation questions (e.g., "Is that right?") too early in the conversation when confidence is low, rather than continuing the discovery loop.
3. **Friction Overload (Friction Overload Constraint / The Anti-Scattergun Rule):** Generating overwhelming lists of hypothetical operational frictions rather than focusing on the top 2-3 most critical points directly related to the user's specific workflow.

## 2. Goals

1. Enforce **The Fourth Wall Rule (No Metadata Leakage)** across all user-facing prompts in the `context_architect` and `synthesize_report` nodes.
2. Enforce **The Discovery vs. Confirmation Boundary** based on the `e2e_confidence_score` threshold of `0.85` in the `context_architect` node.
3. Enforce **Friction Overload Constraint (The Anti-Scattergun Rule)** in report synthesis to limit friction points to the top 2-3 critical operational bleed points.

## 3. Non-Goals

1. Do not introduce any new graph nodes or change the overall state machine topology.
2. Do not modify the existing schema models or database structures.
3. Do not modify the rate-limiting or Redis budget caps.

## 4. Functional Requirements

### 4.1 The Fourth Wall Rule (No Metadata Leakage)
- The system prompts for the discovery/intake nodes (referred to as `context_architect` prompts, including intake and playback) and the synthesis node (`synthesize_report`) must strictly forbid exposing internal LangGraph state variables or framework labels to the user.
- The agent MUST NEVER print words like `turn_index`, `confidence_score`, `Trigger`, `Actor`, `System`, or `Friction` (case-insensitive) in its user-facing output.
- All internal state logic, completeness metrics, and routing choices must be translated into natural, conversational English before being presented to the user.

### 4.2 The Discovery vs. Confirmation Boundary
- Update the discovery behavior based on the `e2e_confidence_score` value:
  - **Discovery Mode (`e2e_confidence_score < 0.85`)**: The agent is strictly forbidden from ending its turn with a closed confirmation like "Is that right?" or summarizing the workflow for confirmation. It MUST end the turn using the **Neutral Gap** rule to ask about the next highest-priority blind spot or missing detail.
  - **Confirmation Mode (`e2e_confidence_score >= 0.85`)**: The agent may summarize the workflow and ask for final confirmation (e.g., playback summary) before routing the state machine to report synthesis.

### 4.3 Friction Overload Constraint (The Anti-Scattergun Rule)
- Update the `synthesize_report` system prompt to cap the Friction Analysis section of the final output.
- The agent must limit its deduced friction points to the **Top 2 or 3 most critical operational bleed points** directly related to the user's specific workflow.
- The agent is strictly forbidden from generating an exhaustive, 6-point matrix of hypothetical frictions across every unverified business pillar.

## 5. Acceptance Criteria

1. Live assistant responses generated by intake, playback, or synthesis nodes do not contain internal framework labels (such as `turn_index`, `confidence_score`, `Trigger`, `Actor`, `System`, or `Friction`).
2. Discovery turns with `e2e_confidence_score < 0.85` never end with closed confirmations (e.g., "Is that right?") or playback summaries, but rather ask a Neutral Gap question.
3. Playback summaries and confirmation questions are only displayed/sent when `e2e_confidence_score >= 0.85`.
4. Synthesized reports contain exactly 2 or 3 critical operational bleed points in the Friction Analysis section, rather than an exhaustive 6-pillar list.
5. All existing tests and E2E evaluations pass without regressions.

