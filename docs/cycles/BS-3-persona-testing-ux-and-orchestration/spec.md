# Persona Testing UX and Orchestration Fixes (BS-UX-ORCHESTRATION)

## Problem Statement
During a persona testing session, several significant UX and orchestration gaps were discovered:
1. **BUG-041 (Missing Handoff):** The transition from dialogue to the final report lacks a conversational conclusion message, making the app appear unresponsive when orchestration finishes.
2. **BUG-042 (Intake Shallowness):** The consultative intake over-indexes on operations and fails to deeply explore other pillars (budget, risk, market) before handing off to recommendations.
3. **BUG-043 (No Cross-Project Memory):** Foundational company knowledge (like location) is not shared across projects for the same company, leading to redundant questions. The intake text extraction also silently drops meta-questions.
4. **BUG-044 (Static Flowchart):** The Interactive Graph / Flowchart UI renders generic, hardcoded SaaS boilerplate instead of actual session-driven data.
5. **BUG-045 (Raw Project Titles):** Project titles in the dashboard are naively derived from raw user messages rather than semantic summaries.

## Goal
To resolve these UX and orchestration gaps to provide a seamless, robust, and intelligent user experience that correctly leverages context and provides clear transitions.

## Scope of Changes
1. **Dialogue Transition (BUG-041):** Add an explicit "completion" or "handoff" message from the agent when all required pillars are covered, auto-navigating or clearly instructing the user to view the Executive Report.
2. **Intake Gating (BUG-042):** Update the orchestrator's missing-information prompt or gating logic to enforce exploration of all six pillars (market, operations, financials, personnel, technology, risk) before concluding discovery.
3. **Cross-Project Memory (BUG-043):**
    *   Hydrate basic company profile information into the `SessionState` context upon session creation so the agent avoids redundant questions.
    *   Adjust the intake text cleaner prompt to preserve user meta-questions (e.g., "do you remember what I said last time?") rather than aggressively filtering them.
4. **Dynamic Flowchart View (BUG-044):** Update the Interactive Graph UI component to consume actual `SessionState` or synthesis report metrics rather than rendering static boilerplate.
5. **Semantic Project Titles (BUG-045):** Implement a lightweight LLM call or semantic summarization step during session creation or post-intake to generate a concise, relevant project title instead of using raw message text.

## Acceptance Criteria
- [ ] **BUG-041:** The agent emits a final concluding message in the chat upon completing the six pillars, and the UI provides clear transition signaling.
- [ ] **BUG-042:** Evaluators/Tests confirm the agent will ask questions spanning multiple pillars (e.g., budget, risk) before entering confirmation/synthesis.
- [ ] **BUG-043:** A second project under the same company does not ask for the company location if it was established in the first project. Meta-questions are not silently dropped.
- [ ] **BUG-044:** The Interactive Graph view displays business-specific context (e.g., specific margins or operational details) derived from the current session instead of generic SaaS metrics.
- [ ] **BUG-045:** Dashboard project titles display contextual summaries (e.g., "Woodworking quoting process") instead of raw user dialogue.
