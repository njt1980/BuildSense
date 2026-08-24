# System Design: Persona Testing UX and Orchestration Fixes (BS-UX-ORCHESTRATION)

## Architecture & Data Flow

This cycle introduces refinements across the orchestration engine (backend) and React application (frontend) to address gaps discovered during persona testing.

1.  **Dialogue Transition (BUG-041):** The orchestrator's final node, `_node_synthesize_report`, will now explicitly append an assistant message to `state["messages"]`. This message acts as a conversational capstone, directing the user to the Executive Report tab, thereby avoiding a silent UX failure.
2.  **Intake Gating (BUG-042):** To ensure a well-rounded business audit, `build_iterative_discovery_metadata` and the surrounding routing logic will integrate a Six-Pillar completeness check. The `confidence` score generation will be penalized if the accumulated evidence ledger lacks representation in key pillars (e.g., Financials/Budget, Risk, Personnel), ensuring the bot asks about these before `should_synthesize_now` becomes true.
3.  **Cross-Project Memory (BUG-043):**
    *   **Context Hydration:** When a new project session is created in `/api/v1/projects` or `/api/v1/orchestrate`, we will extract existing firmographic baseline details (like location, company name, domain) from the user's previously saved company profile and inject them into the initial `SessionState.messages` as a system context primer or directly into `SessionState.metadata`.
    *   **Meta-Question Protection:** The regex/LLM prompt in `_node_sanitize_input` (or text extraction) will be tuned to stop discarding meta-conversational text (e.g., "do you remember what I said last time?") so the orchestrator can answer these accurately.
4.  **Dynamic Flowchart View (BUG-044):** The React Flow visual graph generation in `_node_synthesize_report` (which hardcodes SaaS strings like "LTV:CAC ratio > 3x") will be rewritten to extract insights from the dynamically generated `roi_economics`, `friction_analysis`, and `as_is_workflow` metadata.
5.  **Semantic Project Titles (BUG-045):** In `apps/web` or the `/api/v1/projects` creation route, we will replace the raw `message[:50]` fallback with a lightweight semantic naming function.

## Atomic Implementation Steps

### Step 1: Dialogue Transition (BUG-041) & Dynamic Flowchart (BUG-044)
*   **Target Files to Read:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_orchestrator.py`
*   **Target Files to Modify:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_orchestrator.py`
*   **Action:** 
    1. In `_node_synthesize_report`, map the `nodes` and `edges` definition for the visual graph to actual session metadata (`state_metadata['as_is_workflow']`, `state_metadata['roi_economics']`, etc.) instead of hardcoded SaaS boilerplate strings. Ensure edges have valid source/target mapping to render correctly.
    2. At the end of `_node_synthesize_report`, append a new HumanMessage/AIMessage to `state["messages"]` (e.g., `"I have completed my analysis. Your Executive Report is ready..."`) and save it to the intermediate state so the frontend displays a concluding conversational turn.

### Step 2: Intake Gating & Six-Pillar Depth (BUG-042)
*   **Target Files to Read:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_interview.py`
*   **Target Files to Modify:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_interview.py`
*   **Action:** In `build_iterative_discovery_metadata` and `build_six_pillar_coverage`, adjust the confidence scoring logic to require active coverage in Financials, Risk, and Personnel pillars. The `should_synthesize_now` flag should remain false if these pillars are empty, pushing the agent to ask follow-up questions about budget and key-person risk.

### Step 3: Cross-Project Memory & Context Preservation (BUG-043)
*   **Target Files to Read:** `apps/api/app/core/orchestrator.py`, `apps/api/app/main.py`
*   **Target Files to Modify:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_orchestrator.py`
*   **Action:**
    1. Pass existing company facts (like location and business type) into the initial session state or context architect so the model has awareness of the parent company across projects.
    2. Adjust the system prompt for extraction/sanitization to explicitly instruct the model to preserve user meta-questions (e.g., references to past memory or context) in the sanitized output.

### Step 4: Semantic Project Titles (BUG-045)
*   **Target Files to Read:** `apps/web/src/app/[lang]/page.tsx`, `apps/api/app/main.py`
*   **Target Files to Modify:** `apps/api/app/main.py`, `apps/api/app/db/postgres.py` (if necessary)
*   **Action:** Update the `/api/v1/projects` POST route or equivalent project creation logic. If the user payload provides a raw chat message as a title, apply a lightweight regex, heuristic, or LLM call to synthesize a concise, semantic project title (e.g., "Woodworking Quote Workflow") before persisting it to the database.
