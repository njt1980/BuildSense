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
