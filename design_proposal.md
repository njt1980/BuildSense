# Design Proposal: BuildSense End-to-End Evaluation Suite

This proposal details the architecture, file structure, dataset schema, and assertion strategy to implement a systematic End-to-End Evaluation Suite (`apps/api/tests/evals/`) for the BuildSense LangGraph orchestrator (`orchestrator.py`).

---

## 1. Proposed File Structure

We will isolate the evaluation suite under `apps/api/tests/evals/` to avoid mixing integration/eval tests with unit tests:

```
apps/api/
└── tests/
    └── evals/
        ├── __init__.py
        ├── conftest.py       # Global database/cache mocks & custom pytest terminal summary reporter
        ├── eval_dataset.py   # Dataset definitions & multi-turn exchange structures
        ├── judge.py          # Claude 3.5 Haiku judge client & semantic grading rubrics
        └── test_runner.py    # Pytest E2E orchestrator assertions (routing & state accumulation)
```

---

## 2. Dataset Schema & Test Scenario Construction

We will define our scenarios in `apps/api/tests/evals/eval_dataset.py`. The schema structure is designed to represent both single-input routing prompts and ordered multi-turn interactions.

### Dataset Schema (`EvalScenario`)

We will use TypedDict definitions for clean schema modeling:

```python
from typing import Any, Dict, List, Optional, TypedDict

class Turn(TypedDict):
    user_input: str
    expected_status: str
    expected_components: Dict[str, Any]  # Key-value assertions on process_components

class EvalScenario(TypedDict):
    name: str
    mode: str
    motivation: str
    turns: List[Turn]
    expect_synthesis: bool               # True if this scenario completes the entire workflow
    user_constraints: Optional[List[str]]
```

### The 5 Golden Scenarios

1. **Short Starter Chips (HITL Clarification)**
   - **Input**: `"Walk through customer order"` (< 50 characters)
   - **Assertion**: Immediately routes to `SessionStatus.AWAITING_CLARIFICATION`, `playback_confirmed=False`, and asks ontology questions.

2. **Messy Multi-Turn Conversation (Intake Accumulation)**
   - **Input Flow**:
     - **Turn 1**: `"I run a pet shop."` (Assesses vertical, updates state, asks clarification).
     - **Turn 2**: `"We receive orders on WhatsApp."` (Updates trigger/source, asks clarification).
     - **Turn 3**: `"I manually type them into Excel."` (Completes the mandatory components loop, presents Playback summary).
   - **Assertion**: Each turn updates `state.process_components` fields. After Turn 3, `process_components` contains `actor="pet shop staff/owner"`, `system="Excel"`, and `trigger="WhatsApp orders"`.

3. **The Escape Hatch (Fallback to Unknown)**
   - **Scenario A (User input "I don't know")**:
     - **Input**: `"I don't know what tools they use."`
     - **Assertion**: System forcefully fills missing components (`system` or `actor`) with `"UNKNOWN"` and presents the Playback Summary.
   - **Scenario B (Clarification Turn limit = 2)**:
     - **Setup**: Inject state with `clarification_turns = 2` and submit a vague query.
     - **Assertion**: Gracefully falls back to `"UNKNOWN"` for missing slots and enters Playback.

4. **Correction Handling (State Mutation & Re-Playback)**
   - **Input Flow**:
     - **Turn 1**: High completeness input triggering Playback (e.g., invoice tracking via Excel).
     - **Turn 2**: User rejects the Playback Summary with corrections: `"No, we use Tally, not Excel."`
     - **Assertion**: The `system` component in `process_components` changes from `"Excel"` to `"Tally"`, `playback_confirmed` remains `False`, and a new Playback Summary mentioning "Tally" is emitted.

5. **Full Workflow to Execution & Synthesis**
   - **Input Flow**:
     - **Turn 1**: Full business process details.
     - **Turn 2**: Confirming playback summary: `"Yes, correct."`
   - **Assertion**: State transitions from `ROUTING` -> `AWAITING_CLARIFICATION` -> `PLANNING` -> `EXECUTING` -> `COMPLETED`. Mocks tool executions and builds a full synthesis report.

---

## 3. Deterministic State Machine Assertions

We will build a test runner in `test_runner.py` that imports `orchestrator` and runs `run_pipeline` programmatically. 

### Turn Loop Simulation
For multi-turn tests, the runner will iteratively invoke `orchestrator.run_pipeline` by appending the new user message to the output state's messages and passing it to the next step:
```python
state = SessionState(...)
for turn in scenario["turns"]:
    state.messages.append(Message(role="user", content=turn.user_input))
    state = await orchestrator.run_pipeline(state)
    assert state.status == turn.expected_status
    # Assert specific process components mutations
    for k, v in turn.expected_components.items():
        assert getattr(state.process_components, k) == v
```

### Safety & Loop Protections
- Assertion that `steps_taken` does not exceed `max_steps`.
- Verification that session status transitions to `SessionStatus.FAILED` if budget or step limits are breached, avoiding infinite loop traps.

---

## 4. LLM-as-a-Judge Semantic Assertions

We will build a lightweight judge in `judge.py` calling `claude-3-5-haiku-20241022` to score generated outputs.

### Grading Criteria & Rubrics
1. **Zero-Jargon Compliance**:
   - Check if jargon terms like *ROI*, *LTV*, *CAC*, *MRR* are accompanied by everyday analogies in parentheses.
2. **Recommendation Hierarchy Integrity**:
   - Ensure the recommendations section evaluates Tier 1 (Process/Policy Change) and Tier 2 (Deterministic SaaS/Automation) before suggesting Tier 3 (Gen AI/Agents).
3. **Playback Formatting**:
   - Verify that Playback Summaries utilize scannable emoji-bulleted Markdown lists with the custom emojis (`🚚`, `👤`, `⚙️`, `💻`, `⚠️`).

### JSON Output Schema
```json
{
  "zero_jargon_score": float,         // Range 0.0 - 1.0 (threshold >= 0.90)
  "hierarchy_integrity_score": float, // Range 0.0 - 1.0 (threshold >= 0.90)
  "playback_formatting_score": float,  // Range 0.0 - 1.0 (threshold >= 0.90)
  "justification": "string"
}
```

If the API key is not present in the local environment, the judge will fail gracefully and return mock passing scores (`1.0`) to avoid blocking local developer pipelines.

---

## 5. Custom Execution CLI & Terminal Reporter

The evaluation suite will be executed with:
```powershell
pytest apps/api/tests/evals
```

We will implement `pytest_terminal_summary` inside `apps/api/tests/evals/conftest.py` to capture test execution duration (latency) and status. It will render a clean terminal summary:

```
========================= E2E EVALUATION REPORT =========================
SCENARIO NAME                               STATUS    LATENCY (s)
-------------------------------------------------------------------------
Vague Starter Chip Clarification            PASSED    0.12s
Messy Multi-Turn Intake Accumulation        PASSED    2.84s
The Escape Hatch Fallback                   PASSED    0.15s
Correction Handling & Re-Playback           PASSED    1.22s
Full Workflow Execution & Synthesis         PASSED    4.52s
-------------------------------------------------------------------------
Overall Pass Rate: 100.0% | Total Latency: 8.85s
=========================================================================
```
