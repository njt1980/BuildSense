# Specification: Faster Workspace Navigation And Evaluation Flow

## 1. Problem

The dashboard workflow submission currently waits for the full `/api/v1/orchestrate` request before navigating to the project workspace. Users see `Scaffolding Workspace...` for the duration of the first orchestration pass, which can take roughly 20-30 seconds on local runs.

After navigation, the project workspace can trigger another orchestration request during page mount when an existing session is found. Users then see `Evaluating...` and `Reviewing workflow...` even when the previous request already created or paused the same session. This creates duplicated work and makes the app feel slow.

## 2. Goals

1. Navigate from the dashboard to the workspace as soon as the project record exists.
2. Avoid automatically re-running orchestration on project page mount when session state already exists.
3. Preserve the existing chat-first clarification behavior once the workspace loads.
4. Keep the `Run Analysis` button as the explicit way to resume or advance orchestration from the workspace.
5. Keep existing authentication, company ownership, tenant isolation, and session state guardrails intact.

## 3. Non-Goals

1. Do not redesign the visual UI.
2. Do not introduce a new orchestration framework.
3. Do not change prompt behavior or synthesis quality criteria.
4. Do not add production telemetry or external observability services.
5. Do not remove the existing `/api/v1/orchestrate` endpoint.

## 4. Functional Requirements

### 4.1 Dashboard Submission

- When a user submits a new workflow from the dashboard, the frontend must create a project workspace quickly.
- The dashboard must navigate to `/{lang}/projects/{project_id}` after project creation succeeds.
- The dashboard must not block navigation on a full orchestration run.
- The initial workflow text, file metadata/content, constraints, language, company ID, industry context, mode, motivation, and persona must be preserved so the workspace can start or resume orchestration with the same context.

### 4.2 Workspace Load

- The workspace page must load project details, graph data, and existing session state.
- If session state exists, the page must render it without automatically calling `/api/v1/orchestrate`.
- If no session state exists, the page may show the normal chat/start state and let the user explicitly start analysis.
- Existing `AWAITING_CLARIFICATION` sessions must open the Dialogue Panel without kicking off another backend run.

### 4.3 Explicit Evaluation

- Clicking `Run Analysis` must remain the explicit trigger for `/api/v1/orchestrate`.
- Sending a chat message must still submit the message to `/api/v1/orchestrate`.
- Clarification answers must still submit to `/api/v1/orchestrate`.
- While a request is active, the UI must still prevent duplicate submissions through the existing disabled/loading state.

### 4.4 Backend Support

- The backend must support project creation with enough initial workflow context for a later orchestration call.
- Existing tenant checks must remain enforced on project creation and session access.
- Existing session persistence behavior must remain compatible with `get_session`.

## 5. Acceptance Criteria

1. Submitting `We are a cab booking company` from the dashboard navigates to the workspace without waiting for a full orchestration run.
2. Loading a project workspace with existing session state does not automatically call `/api/v1/orchestrate`.
3. The Dialogue Panel can display existing assistant/user messages from loaded session state.
4. `Run Analysis`, chat submit, and clarification submit still invoke orchestration.
5. `npm run type-check` passes in `apps/web`.
6. `npm run lint` passes in `apps/web`.
7. Relevant backend tests pass for project/session/orchestrator behavior.
8. No secrets, `.env`, runtime logs, caches, virtual environments, or `node_modules` files are staged.

## 6. Risks And Constraints

- The current dashboard uses `/api/v1/orchestrate` as both project creation and analysis kickoff, so separating these concerns must preserve user-entered workflow context.
- The project page currently keeps orchestrator state inside `useOrchestratorStream`; loading existing session state may require the hook to expose a setter or hydration method.
- Local development runs may still spend time on explicit analysis because LLM-backed sanitization, extraction, and clarification generation remain intentionally synchronous.
