# Specification: Safe Deterministic Confirmation Gate & Consolidated Consulting Synthesis

## 1. Goal Description
To improve user experience, reduce backend response latency, and fix duplicate assistant questions, we are optimizing the BuildSense orchestrator to:
1. Implement a **Safe Deterministic Confirmation Gate** that instantly processes simple yes/no responses (including synonyms like `"yep"` or `"nope"`) without calling the LLM, while falling back to the LLM for nuanced inputs (like `"Yes, but..."`).
2. **Isolate Worker Prompts** in the backend DAG execution phase, ensuring worker personas (`Process Analyst` and `Automation Architect`) perform background analyses without leakage of orchestrator-level interview instructions that cause redundant user questions.
3. **Reduce Latency** by running independent worker tasks in parallel.
4. Adopt a **Friendly, Fun, and Human-like Tone** in all user-facing interactions to build rapport and keep the discovery experience engaging.

---

## 2. Functional Requirements

### 2.1 Safe Deterministic Confirmation Check
- Normalize the user's prompt by converting it to lowercase and removing common trailing punctuation (e.g. `!`, `.`, `?`, `,`).
- Define exact match sets:
  - **Confirmations**: `{"yes", "yep", "yup", "yea", "yeah", "sure", "ok", "okay", "correct", "accurate", "accurate now", "indeed"}`
  - **Denials**: `{"no", "nope", "wrong", "incorrect", "not correct", "not accurate"}`
- If the prompt matches a word in either set, set `playback_confirmed` directly to `True` (for confirmation) or `False` (for denial), and **bypass** the LLM `confirm_gate` API call.
- If the response is longer than 2 words, or contains qualifying words (like `"but"`, `"except"`, `"actually"`, `"instead"`), the bypass **must not** occur; the orchestrator must fall back to the LLM `confirm_gate` to classify the input and extract updated components.

### 2.2 Worker Prompt Isolation & Question Suppression
- In the task execution node (`_node_execute_tools`), the system prompts for worker personas must **not** include the general orchestrator prompt (`_build_system_guidance`).
- Worker personas must receive specific system prompts instructing them to analyze the As-Is process or design the To-Be automation solutions in the background, explicitly stating they are running as a background task and **must never** ask questions or prompt the user.

### 2.3 Parallel Task Execution
- Update [`_node_execute_tools`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/core/orchestrator.py) to run both independent DAG tasks (`deconstruct_workflows` and `design_automations`) in parallel using `asyncio.gather` instead of executing them sequentially in separate graph loops.

### 2.4 Friendly, Fun, and Human-like Tone
- Update the system instructions in `CONSULTANT_INTAKE_PROMPT` and `CONSULTANT_PLAYBACK_PROMPT` to enforce a friendly, fun, encouraging, and human-like tone:
  - Use warm greetings (e.g. *"Perfect!"*, *"Got it, thanks!"*, *"Great, let's keep moving!"*).
  - Use relatable metaphors and encouraging feedback.
  - Avoid dry, robotic, or overly corporate phrasing.

---

## 3. Non-Functional Requirements & Latency Targets
- **Latency**: Reduce total execution latency for confirming playback and generating the report by 30-50% (saving 1-2 Sonnet round-trips and 1 Haiku call).
- **Correctness**: Maintain 100% routing accuracy on simple confirmations and denials.

---

## 4. Acceptance Criteria
1. Synonyms like `"yep"`, `"yup"`, `"sure"`, `"correct"` instantly confirm the playback and advance the graph without invoking the Haiku LLM classifier.
2. Synonyms like `"nope"` or `"wrong"` reject the playback and prompt for correction without invoking the Haiku LLM classifier.
3. Complex responses like `"Yes, but we also use Excel"` trigger LLM extraction and successfully add "Excel" to the system components.
4. Worker personas do not output duplicate questions in the conversation history during Phase 3.
5. All automated unit tests in `test_orchestrator.py` pass.
6. The agentic quality evaluations (`test_agent_quality.py`) score above 90% on zero-jargon, factuality, routing, and consultant quality metrics, with judge verification that the tone is friendly and human-like.

---

## 5. Verification Plan
- Run unit tests: `pytest apps/api/tests/ -v`
- Run agentic evaluation suite: `pytest apps/api/evals/test_agent_quality.py -v --run-evals`
