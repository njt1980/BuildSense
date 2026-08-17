# Specification: Dynamic Discovery and Evaluation Patches

## 1. Goal Description

This specification outlines the backend LangGraph orchestrator and prompt changes required to implement "Iterative Discovery" using elite consulting frameworks, patch behavioral drifts caught by LLM-as-a-judge evaluations, and handle users who provide a "Blank Canvas" (industry only, no specific problem description).

The updates cover routing logic changes, intake bifurcation, prompt constraint enforcement, fallback behavior for low-confidence turn-three runs, and synthesis output formatting rules.

---

## 2. Functional Requirements

### 2.1 Iterative Discovery Loop & Routing (LangGraph)
- **MAX_CLARIFICATION_TURNS**: Define and enforce an internal limit of `MAX_CLARIFICATION_TURNS = 3`.
- **e2e_confidence_score Check**: The graph's routing node (`route_intent`) must inspect `e2e_confidence_score` and `clarification_turns`:
  - **Loop back to Context Architect**: If `e2e_confidence_score < 0.85` and `clarification_turns < 3`, the routing logic must loop back to `context_architect` (via the checkpointer / user-facing await-human cycle) to continue discovery.
  - **Synthesize Report**: If `e2e_confidence_score >= 0.85` (or playback confirmed), OR if `clarification_turns >= 3`, the orchestrator must transition the graph state to `synthesize_report`.

### 2.2 Dynamic Intake (The "Blank Canvas" Fallback)
- **Bifurcation Trigger**: In `context_architect`, check if the user has provided any specific friction or pain points (`components.get("friction") == null` or empty).
  - **Path A (Friction Provided)**: Proceed with the standard discovery flow: a Consultative Handshake validation followed by Neutral Gap questions.
  - **Path B (Blank Canvas - e.g., "Family-owned restaurant")**: If no friction is provided, the agent is strictly forbidden from asking abstract automation questions (e.g., "What process do you want to automate?"). Instead, it must execute a **"Seed and Story"** conversational prompt:
    - **The Seed**: List 2 or 3 highly specific, relatable operational pain points typical for the user's identified industry.
    - **The Story**: Acknowledge the industry, and immediately ask the user to describe the first two hours of their day to identify where their specific friction lies.
    - **Format**: The prompt response must consist of entirely conversational plain text with no UI chips, buttons, or suggestions.

### 2.3 Discovery vs. Confirmation Boundary
- **Discovery Mode (`e2e_confidence_score < 0.85`)**:
  - The agent is strictly forbidden from ending its turn with a closed summary or closed confirmation query like "Is that right?", "Is this correct?", or summarizing the entire flow for verification.
  - The agent MUST end the turn using the **Neutral Gap** rule, which anchors on a known fact from the user's response and asks an open-ended "How" or "What" question to map the next workflow step.
- **Confirmation Mode (`e2e_confidence_score >= 0.85`)**:
  - The agent may summarize the end-to-end workflow details and ask the user for final confirmation (e.g. playback summary) before proceeding to synthesis.

### 2.4 The Fourth Wall Rule (No Metadata Leakage)
- The assistant's output to the user MUST NEVER expose internal LangGraph state variables, framework labels, database keys, or classification tags.
- Specifically, the output must not print words like:
  - `turn_index` / `turn_count`
  - `confidence_score` / `e2e_confidence_score`
  - `Trigger` / `Actor` / `System` / `Activity`
  - `Market Pillar` / `Pillar`
  - `Friction`
- Any internal state rules or completeness status must be translated into natural, conversational English.

### 2.5 The "Ambiguity Fallback" (Handling Turn 3 Dead-Ends)
- If the graph reaches `clarification_turns == 3` but the `e2e_confidence_score` remains low (e.g., `< 0.85` or the user provided ambiguous/vague answers), the `synthesize_report` node must execute a graceful exit:
  - **Unverified Assumptions**: State an explicit "Unverified Assumptions" block outlining what was missing or unconfirmed during discovery.
  - **No Hallucination**: Do NOT invent or assume missing database tools, staff roles, tools, or process steps.
  - **Process Principles**: Recommend zero-cost "Process Principles" (e.g., standardizing communication channels, setting up email folder labels) rather than specific software tools, automation platforms, or CRMs.

### 2.6 Synthesis Constraints (Anti-Scattergun & Iceberg Delivery)
- **Friction Overload Constraint**: The report must limit its deduced friction points to the **Top 2 or 3** most critical operational bleed points. The agent is strictly forbidden from generating an exhaustive 6-pillar matrix or scattergun list of minor hypothetical frictions.
- **Iceberg Delivery / Next Horizons**: The final report must focus on solving the immediate, high-priority bleeding-neck problem first. At the end of the report, the agent must append a "Next Horizons" section highlighting exactly one adjacent business pillar or improvement area that was intentionally deferred.

---

## 3. Golden Transcripts (Behavioral Anchors)

### Scenario 1: The Blank Canvas (Path B)
- **User**: "Family-owned restaurant."
- **Agent (Seed & Story)**: "Family restaurants have a unique rhythm. Often, the biggest leaks I see are tracking supplier invoices, managing shift swaps, or the chaos of front-of-house reservations. To help me spot where your specific friction is, walk me through the first two hours of your day. From the moment you unlock the doors, what is the very first fire you usually have to put out?"

### Scenario 2: The Bleeding Neck (Path A)
- **User**: "Wholesale texts at midnight."
- **Agent (Handshake)**: Acknowledges texts, asks permission to view E2E kitchen flow.
- **User**: "Yeah, that's fine."
- **Agent (Neutral Gap)**: "How does info get from your phone to the bakers?" (Note: Agent does NOT ask 'Is this right?' because confidence is low).
- **User**: "I write it on a notepad."
- **Agent (Confirmation Turn)**: Confidence is high. Summarizes the E2E flow and asks for confirmation.
- **Synthesis**: Top 2 frictions only. Solves intake via Google Forms. Next Horizon: Ingredient procurement.

---

## 4. Acceptance Criteria

1. **Routing Rules**: Routing loops back to `context_architect` via human clarification turns when `clarification_turns < 3` and `e2e_confidence_score < 0.85`. Synthesis is triggered when `clarification_turns >= 3` or when `e2e_confidence_score >= 0.85` (after confirmation).
2. **Blank Canvas Logic**: Input with empty or null friction bypasses the Consultative Handshake/Neutral Gap flow and triggers the "Seed and Story" prompt.
3. **No Metadata Leakage**: System prompts strictly block leakage of internal state variables (`turn_index`, `confidence_score`, `Trigger`, `Market Pillar`, `Friction`).
4. **Boundary Compliance**: Discovery Mode responses do not summarize or ask "Is that right?" questions. Confirmation Mode is only active when `e2e_confidence_score >= 0.85`.
5. **Fallback Synthesis**: Report generated on turn 3 with low confidence uses the Ambiguity Fallback: lists "Unverified Assumptions", recommends process-first principles, and contains zero software recommendations.
6. **Synthesis Constraints**: Final report lists at most 2-3 operational frictions and includes a "Next Horizons" section highlighting one adjacent business pillar left out.

---

## 5. Verification Plan

### 5.1 Automated Unit & Integration Tests
- **Routing & Loops**: Write tests verifying routing behavior when `e2e_confidence_score` is low at turn 1, 2, and 3.
- **Blank Canvas**: Write tests verifying that a blank canvas input triggers the `seed_and_story` strategy.
- **Metadata Filter**: Write tests asserting that the string output does not contain forbidden words.
- **Synthesis Limits**: Write tests verifying report content length and formatting restrictions (Friction counts, Unverified Assumptions block, Next Horizons presence).

Run backend tests using:
```powershell
cd apps/api
pytest tests/test_interview.py tests/test_orchestrator.py -v
```

### 5.2 LLM-as-a-judge Evaluation Suite
Run the evaluation suite with the live judge:
```powershell
cd apps/api
pytest evals/ -v --run-evals
```
Verify the zero-jargon, hallucination, and consultant intake scores remain > 90% and there are no behavioral regressions.
