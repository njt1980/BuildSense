# System Design: Safe Deterministic Confirmation Gate & Consolidated Consulting Synthesis

## 1. Architecture & Telemetry Data Flow

The optimized orchestrator modifies the graph execution flow:

```text
User Input
   │
   ├──► route_intent (Awaiting Playback Confirmation)
   │      │
   │      ├──► [Normalizer] check_deterministic_confirmation
   │      │      ├──► Matches (yes/no synonyms) ──► Sets playback_confirmed ──► Skip Haiku confirm_gate LLM
   │      │      └──► Nuance ("Yes, but...") ──► Claude Haiku confirm_gate LLM (extracts new components)
   │      │
   │      └──► If playback_confirmed == True: Advances to PLANNING/EXECUTING
   │
   └──► execute_tools Node
          │
          └──► Concurrently runs Process Analyst & Automation Architect tasks via asyncio.gather
                 - System prompts do NOT include general orchestrator system prompt
                 - Workers act in background (analysis only), producing no user-facing questions
```

---

## 2. Component Design & Changes

### 2.1 Safe Deterministic check
- Create `check_deterministic_confirmation(user_prompt: str) -> Optional[bool]` inside `orchestrator.py`.
- Strips punctuation and matches against confirmation/denial sets.
- Integrates with `_node_route_intent` at the confirmation classifier gate.

### 2.2 Worker Prompt Separation & Background Enforcement
- Define distinct system prompts in `orchestrator.py` for worker tasks:
  - `PROCESS_ANALYST_WORKER_PROMPT`: Instructs the model to deconstruct workflow steps, identify friction, and map evidence on the Evidence Ladder.
  - `AUTOMATION_ARCHITECT_WORKER_PROMPT`: Instructs the model to analyze technology constraints and draft automation designs.
  - Both prompts explicitly forbid asking the user questions or returning interactive chat messages.

### 2.3 Concurrency (Parallel Execution)
- In `_node_execute_tools`, group worker task execution using `asyncio.gather` to concurrently run the tasks in `_execute_live_sdk_loop`.

---

## 3. Atomic Implementation Steps

### Step 1: Implement Safe Deterministic Confirmation Bypass
- **Read/Modify file**: [`orchestrator.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/core/orchestrator.py)
- **Action**: Implement `check_deterministic_confirmation` and update the confirmation gate logic in `_node_route_intent` to call it first, bypassing the LLM classifier for simple inputs.

### Step 2: Implement Unit Tests for Deterministic Confirmation Gate
- **Read/Modify file**: [`test_orchestrator.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/apps/api/tests/test_orchestrator.py)
- **Action**: Add unit tests checking various confirmation synonyms (`"yep"`, `"sure."`, `"yup"`, `"no"`, `"nope"`) and nuance strings (`"yes, but we also use Excel"`, `"no, receptionist handles it"`).

### Step 3: Isolate and Decouple Worker Prompts
- **Read/Modify file**: [`orchestrator.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/core/orchestrator.py)
- **Action**: Define `PROCESS_ANALYST_WORKER_PROMPT` and `AUTOMATION_ARCHITECT_WORKER_PROMPT`. Update `_execute_live_sdk_loop` to use them without appending `_build_system_guidance()`.

### Step 4: Parallelize Worker Task Execution
- **Read/Modify file**: [`orchestrator.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/core/orchestrator.py)
- **Action**: Refactor `_node_execute_tools` to run deconstruct and design tasks concurrently using `asyncio.gather` when executing under OPTIMIZER mode.

### Step 5: Refine Consultant Prompts for Human-like Tone
- **Read/Modify file**: [`orchestrator.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/core/orchestrator.py)
- **Action**: Update `CONSULTANT_INTAKE_PROMPT` and `CONSULTANT_PLAYBACK_PROMPT` to enforce warm, friendly, fun, and human-like interactions.

### Step 6: Expand Golden Dataset
- **Read/Modify file**: [`golden_dataset.json`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/apps/api/evals/golden_dataset.json)
- **Action**: Add scenarios representing physical logistics, wholesale distributor, and manufacturing business cases.

### Step 7: Update and Elaborate Agent Quality Evaluations
- **Read/Modify file**: [`test_agent_quality.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/apps/api/evals/test_agent_quality.py)
- **Action**: Refactor evaluation runner to test multi-turn interactions (initial prompt -> clarification -> confirmation -> report synthesis) and assert zero jargon, grounding, and tone score constraints.

---

## 4. Verification & Testing Design

### 4.1 Automated Validation
- Run unit tests: `pytest apps/api/tests/ -v`
- Run agentic evaluations: `pytest apps/api/evals/test_agent_quality.py -v --run-evals`

### 4.2 Manual Verification
- Deploy local backend and run the client dialogue panel.
- Verify that confirming with `"yep"` bypasses the LLM and instantly completes report synthesis.
- Verify that worker personas do not print intermediate questions on the screen.
- Inspect the generated report to confirm a friendly, jargon-free tone.
