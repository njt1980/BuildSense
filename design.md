# System Design: Dynamic Discovery and Evaluation Patches

## 1. Architecture & Data Flow

The backend orchestrator utilizes LangGraph `StateGraph` for multi-agent routing. The flow is structured around the following sequence:

```text
User Input -> [sanitize_input] -> [context_architect] -> [route_intent] -> [await_human] or [synthesize_report]
```

To support Iterative Discovery, dynamic intake (Blank Canvas), strict boundaries, and evals patches, we will update three key nodes:
1. `context_architect`: Analyzes the user inputs, classifies the strategy (including "Seed & Story"), determines if friction is present, and computes the dynamic intake plan.
2. `route_intent`: Executes the stateful intake step. Performs extraction of workflow components, determines the E2E confidence score, handles user playback/corrections, and builds the next question using prompt strategies.
3. `synthesize_report`: Generates the final analysis. If the discovery loop ended with low confidence, it executes the Ambiguity Fallback.

---

## 2. Component Design & Changes

### 2.1 Iterative Discovery Routing Logic
- **State Fields**: We will track `clarification_turns` and `playback_confirmed` in the Pydantic `SessionState`.
- **MAX_CLARIFICATION_TURNS**: Define a global constant `MAX_CLARIFICATION_TURNS = 3` in `orchestrator.py`.
- **Routing Decision**:
  - In `_node_route_intent`, if `playback_confirmed` is `False`:
    - Calculate `e2e_confidence_score` and update `iterative_discovery` metadata.
    - If `e2e_confidence_score < 0.85` and `clarification_turns < 3`:
      - Increment `clarification_turns` by 1.
      - Set status to `SessionStatus.AWAITING_CLARIFICATION`.
      - Generate the next discovery question based on the selected strategy.
      - Transition to `await_human` (wait for next user response).
    - If `clarification_turns >= 3` or `e2e_confidence_score >= 0.85` (which prompts the playback summary, leading to `playback_confirmed = True` on confirmation):
      - If `clarification_turns >= 3` and confidence remains low, bypass further confirmation and route directly to `synthesize_report` with `ambiguity_fallback = True`.
      - If `playback_confirmed` is `True` (user accepted playback or it is bypassed), set status to `SessionStatus.SYNTHESIZING` and route to `synthesize_report`.

### 2.2 Dynamic Intake ("Blank Canvas" Fallback)
- **Friction Detection**: In `context_architect`, check the value of `components.get("friction")`. If the value is `None`, empty, or matches sentinels, classify the session as a **Blank Canvas** case.
- **Strategy Bifurcation**:
  - **Path A (Friction Provided)**: Use standard discovery. On turn 0, strategy = `handshake`. On subsequent turns, strategy = `neutral_gap` or `multiple_choice_anchor`.
  - **Path B (Blank Canvas)**: If `friction` is null, set `next_question_strategy = "seed_and_story"`.
- **Prompt Execution (Seed & Story)**:
  - When the strategy is `seed_and_story`, the model will be instructed to generate a conversational prompt containing:
    - **The Seed**: List 2-3 specific, relatable, operational friction points typical for that industry vertical (e.g., tracking supplier invoices, managing shift swaps, or table booking chaos for restaurants).
    - **The Story**: Ask the user to describe the first two hours of their day ("walk me through the first two hours of your day. From the moment you unlock the doors, what is the very first fire you usually have to put out?").
  - Constraint: Ensure the text returned is entirely conversational (no markdown buttons, chips, or interactive choices).

### 2.3 Discovery vs. Confirmation Boundary
- **Boundary Enforcement**:
  - **Discovery Mode (`e2e_confidence_score < 0.85`)**:
    - The `CONSULTANT_INTAKE_PROMPT` instructs the LLM that it is in Discovery Mode.
    - The LLM is strictly forbidden from summarizing the workflow or ending with closed confirmation queries (e.g., "Is that right?", "Is this correct?").
    - The LLM must end with a **Neutral Gap** question: an open-ended "How" or "What" question anchored on a known fact.
  - **Confirmation Mode (`e2e_confidence_score >= 0.85`)**:
    - The orchestrator triggers the playback node (`CONSULTANT_PLAYBACK_PROMPT`), which summarizes the accumulated workflow details and explicitly asks the user for confirmation or correction.

### 2.4 The Fourth Wall Rule (No Metadata Leakage)
- Update `CONSULTANT_INTAKE_PROMPT`, `CONSULTANT_PLAYBACK_PROMPT`, and the synthesizer prompts to include strict instructions:
  - "You MUST NEVER print, mention, or expose any internal LangGraph state variables or framework labels in your output."
  - "Specifically, you are strictly forbidden from printing words like 'turn_index', 'confidence_score', 'Trigger', 'Market Pillar', or 'Friction' (case-insensitive) in your user-facing output under any circumstances."
  - "Translate all internal status rules, completeness variables, or structural components into natural, friendly English."

### 2.5 The Ambiguity Fallback
- In `_node_synthesize_report`, check if `iterative_discovery.get("ambiguity_fallback")` is `True` (which is set when turns hit 3 with confidence `< 0.85`).
- If `True`, the synthesis engine changes its output style:
  - **Unverified Assumptions**: Prepend an explicit markdown section:
    ```markdown
    ### Unverified Assumptions
    [Conversational paragraph detailing what facts remain unconfirmed and what the analysis is assuming based on the missing discovery details.]
    ```
  - **No Hallucination**: Do not assume specific software names, tools, databases, or roles.
  - **Process-First Principles**: Recommend zero-cost process changes (e.g., standardizing communication channels, setting manual inbox rules) rather than paid software or custom automations.

### 2.6 Synthesis Constraints
- **Friction Overload Constraint**:
  - The `system_prompt` in `_node_synthesize_report` will be updated to instruct the LLM:
    - Limit deduced friction points to the **Top 2 or 3** most critical operational bleed points.
    - Exhaustive 6-pillar matrices of hypothetical frictions are strictly forbidden.
- **Iceberg Delivery (Next Horizons)**:
  - The report must solve the immediate problem first.
  - Add a **Next Horizons** section at the end of the report body, highlighting exactly one adjacent business pillar or improvement area intentionally left out.
  - Example: "Next Horizons: Once the dedicated email inbox is stable, explore automated e-signature templates."

---

## 3. Prompt Mapping & Templates

### 3.1 `CONSULTANT_INTAKE_PROMPT` Updates
```python
CONSULTANT_INTAKE_PROMPT = """You are BuildSense's intake consultant: a warm, plain-spoken operations consultant for local business owners.
Think "McKinsey for the common man": careful, practical, empathetic, and allergic to jargon.

Your job is to ask the next natural question in a workflow discovery conversation.

THE FOURTH WALL RULE (NO METADATA LEAKAGE):
- You MUST NEVER print, mention, or expose any internal LangGraph state variables or framework labels in your output.
- Specifically, you are strictly forbidden from printing words like "turn_index", "confidence_score", "Trigger", "Market Pillar", or "Friction" (case-insensitive) under any circumstances.
- Translate all internal state logic, completeness rules, or internal structures into natural, conversational English.

DISCOVERY VS. CONFIRMATION BOUNDARY:
- If strategy is "seed_and_story", you are in Discovery Mode. List 2-3 specific, relatable pain points typical for this industry (The Seed). Then immediately ask the user to describe the first two hours of their day (The Story). Output MUST be entirely conversational plain text.
- If strategy is "neutral_gap", you are in Discovery Mode. You are strictly forbidden from ending your turn with a closed confirmation query like "Is that right?", "Is this correct?", or any summary requesting final verification. You MUST end the turn using the Neutral Gap rule: anchor on a known fact and ask one open-ended "How" or "What" question.
- If strategy is "multiple_choice_anchor", you are in Discovery Mode. Acknowledge the vague answer and offer 2-3 relatable options in one question to lower cognitive load.
- If strategy is "handshake", validate the pain, promise to help with the immediate issue, and ask permission to look at the broader workflow.
- Do not use placeholder words like UNKNOWN, null, None, or Not specified.
- Do not invent, assume, or hallucinate systems, software, people, steps, locations, or workflows.

[Grounding Context & Message History Variables...]
"""
```

---

## 4. Verification & Testing Design

### 4.1 Unit & Mock Tests (`apps/api/tests/test_interview.py` & `test_orchestrator.py`)
1. **Routing tests**: Mock the LLM responses to simulate:
   - Low confidence -> loop back to intake up to turn 3.
   - High confidence (>=0.85) -> confirmation summary prompt.
   - Turn 3 low confidence -> direct route to synthesis.
2. **Blank Canvas test**: Mock intake with `friction == None` and assert that the prompt strategy maps to `seed_and_story`.
3. **No Metadata Leakage / Fourth Wall check**: Run assertions on generated assistant messages to ensure forbidden strings are not present.

### 4.2 LLM-as-a-judge Evals
- Execute LLM grading suite using:
  ```powershell
  pytest evals/ -v --run-evals
  ```
- Assert that judge rubrics pass with >=90% compliance on Zero-Jargon and Hallucination metrics.
