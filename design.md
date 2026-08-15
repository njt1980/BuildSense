# Design: Faster Workspace Navigation And Evaluation Flow

## 1. Overview

The fix separates workspace creation from orchestration execution on the dashboard path and prevents the project workspace from automatically re-running orchestration when persisted session state already exists.

The user experience becomes:

```text
Dashboard submit
  -> create project quickly
  -> navigate to workspace
  -> workspace hydrates existing project/session context
  -> user explicitly runs analysis or continues chat
```

This removes the duplicated blocking orchestration call that currently occurs before and after navigation.

## 2. Frontend Changes

### 2.1 Dashboard Page

File:

```text
apps/web/src/app/[lang]/page.tsx
```

Current behavior:

- `handleStartPipeline` sends the dashboard prompt to `/api/v1/orchestrate`.
- The page waits for orchestration to complete before `router.push`.

New behavior:

- `handleStartPipeline` calls `/api/v1/projects` to create the workspace.
- The project payload stores the initial prompt in the project description.
- The frontend sends mode `OPTIMIZER`, motivation `EFFICIENCY`, persona `SMB Operator`, active company ID, and a title derived from the prompt.
- After the project is created, the dashboard stores a small pending intake payload in `sessionStorage` under a key scoped by `project_id`.
- The dashboard navigates immediately to `/{lang}/projects/{project_id}`.

Pending intake payload:

```json
{
  "prompt": "original workflow text",
  "file_name": "optional uploaded file name",
  "file_content": "optional uploaded file content",
  "user_constraints": ["selected constraints"],
  "industry_vertical": "active company industry",
  "user_persona": "SMB Operator",
  "lang": "en"
}
```

The payload is client-side, short-lived, and scoped to the just-created workspace. It avoids schema changes while preserving initial workflow context across navigation.

### 2.2 Orchestrator Hook

File:

```text
apps/web/src/lib/useOrchestratorStream.ts
```

Current behavior:

- The hook owns `activeSessionState` but exposes no hydration method.

New behavior:

- Expose `hydrateOrchestratorSession(state: SessionState | null)`.
- The project workspace can render persisted session state without making a new orchestration request.
- Existing `executeOrchestratorRequest` behavior remains unchanged for explicit analysis/chat/clarification requests.

### 2.3 Project Workspace Page

File:

```text
apps/web/src/app/[lang]/projects/[id]/page.tsx
```

Current behavior:

- On mount, `checkExistingRun` calls `/api/v1/session/{projectId}`.
- If a session exists, it immediately calls `executeOrchestratorRequest({ session_id: projectId, lang })`.

New behavior:

- Rename the behavior to session hydration.
- Load `/api/v1/session/{projectId}` and call `hydrateOrchestratorSession(stateData)`.
- Do not call `/api/v1/orchestrate` during mount when session state exists.
- If a pending intake payload exists in `sessionStorage`, call `executeOrchestratorRequest` once with that payload and `session_id`, then remove the pending payload.
- Keep `Run Analysis`, chat submit, and clarification submit as explicit orchestration triggers.

This means a brand-new dashboard-created workspace can still start analysis automatically after the page appears, but navigation no longer waits for that analysis. Existing workspaces hydrate without duplicate runs.

## 3. Backend Changes

No new endpoint is required for the first implementation.

Existing endpoint used for quick workspace creation:

```text
POST /api/v1/projects
```

Existing endpoint used for session hydration:

```text
GET /api/v1/session/{session_id}
```

Existing endpoint used for explicit orchestration:

```text
POST /api/v1/orchestrate
```

The backend already creates a greeting session if no session exists. The project description stores the initial prompt, while the pending intake payload carries the full submission details into the first explicit orchestration call.

## 4. State And Data Flow

### 4.1 New Dashboard Submission

```text
User submits workflow
  -> POST /api/v1/projects
  -> sessionStorage[pending-intake:{project_id}] = intake payload
  -> router.push(project workspace)
  -> workspace loads project, graph, session
  -> workspace consumes pending intake
  -> POST /api/v1/orchestrate happens after page is visible
```

### 4.2 Existing Workspace Load

```text
User opens workspace
  -> load project details
  -> load graph
  -> GET /api/v1/session/{project_id}
  -> hydrate hook state
  -> no automatic orchestrate call
```

### 4.3 Explicit Follow-Up

```text
User clicks Run Analysis or sends chat
  -> POST /api/v1/orchestrate
  -> hook updates activeSessionState
```

## 5. Validation Plan

Frontend:

```powershell
cd apps/web
npm run type-check
npm run lint
```

Backend focused checks:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m pytest tests/test_companies.py tests/test_orchestrator.py tests/test_interview.py -q
```

Manual browser validation:

1. Submit `We are a cab booking company` from the dashboard.
2. Confirm the workspace route appears quickly.
3. Confirm the workspace shows `Evaluating...` only after the page is visible.
4. Refresh the workspace.
5. Confirm refresh hydrates state without auto-triggering another evaluation.
6. Click `Run Analysis` and confirm evaluation still runs.

## 6. Risks And Mitigations

- Risk: Pending intake in `sessionStorage` can be lost on browser storage clearing.
  - Mitigation: The project still exists with the prompt-derived title/description, and the user can continue through chat.

- Risk: Auto-start after navigation may still feel slow.
  - Mitigation: The page becomes visible first, and future streaming/progress work can improve perceived feedback further.

- Risk: Existing sessions may rely on mount-time orchestration.
  - Mitigation: Keep explicit `Run Analysis`, chat submit, and clarification submit paths unchanged.
