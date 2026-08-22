# Specification: Resolve BUG-048 (Company Binding) & BUG-043 (Cross-Project Memory)

## 1. Overview
Currently, the application suffers from two critical architectural gaps regarding companies and projects:
1. **Wrong Company Binding (BUG-048):** There is no UI to create a second company. New projects are forced onto whichever company is currently active, mixing data.
2. **Fact Amnesia / No Cross-Project Memory (BUG-043):** The `session_memory` (RAG) feature exists in the database schema but is not fully wired into the orchestrator, and it isolates memory strictly by `project_id`. This causes the system to forget foundational facts (like location) between projects within the same company.

We will resolve both issues to establish a robust multi-project, multi-company architecture.

## 2. Requirements & Scope

### 2.1 UI Addition: Create New Company (BUG-048)
- Add a "➕ Create New Company" option to the company switcher dropdown in the global header (`apps/web/src/components/global-header.tsx`).
- Clicking this opens a modal that collects: Business Name, Industry Vertical, Core Tools.
- Upon creation, the application automatically sets the new company as the `activeCompany`. Subsequent project creations will bind to this new company.

### 2.2 Cross-Project Memory Sharing (BUG-043)
- **Database Query Update:** Update the vector search logic (`search_session_memory` in `apps/api/app/db/postgres.py`) to query all memories across all projects that belong to the current project's `company_id`.
- **Orchestrator Wiring:** Integrate `add_session_memory` and `search_session_memory` into the orchestrator (`apps/api/app/core/orchestrator.py`):
  - *Retrieval:* During intake (or architect planning), search the company's memory for relevant facts and inject them into the system prompt.
  - *Storage:* When the session successfully synthesizes or confirms a new fact (or upon completion), store key findings in `session_memory`.

## 3. Out of Scope
- Full user management or login page rewrites (the mock auth remains in place; the UI addition solves the structural issue).
- Changing the underlying vector database technology (we will continue using `pgvector`).

## 4. Acceptance Criteria
- A user can create a new company via the global header dropdown.
- Creating a new project immediately after binds it to the newly created company.
- Facts stated in Project A (e.g., "We are located in Portland, OR") are remembered in Project B (assuming both belong to the same company) without the user having to repeat them.
