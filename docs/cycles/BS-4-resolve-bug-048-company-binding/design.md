# System Design: Resolve BUG-048 & BUG-043 (Phase 2)

## Architecture & Data Flow

This design addresses the multi-tenant architecture gaps around companies and projects, ensuring users can navigate distinct business entities and that memory is structurally shared within a company.

### BUG-048: Create New Company UI
- The global header (`apps/web/src/components/global-header.tsx`) currently has a `Dropdown` for switching active companies.
- We will add a "âž• Create New Company" button inside this dropdown.
- This button will toggle a new `isCreateCompanyModalOpen` state.
- A modal form (rendering over the UI) will collect: `Business Name`, `Industry Vertical`, and `Core Tools`.
- Submission will call the existing `createCompany(name, industry, tools)` method from the `CompanyContext`.
- `CompanyContext` already handles updating the state and setting the new company as active. Subsequent project creations will naturally inherit this new `activeCompany.id`.

### BUG-043: Cross-Project Memory (DB Layer)
- The vector retrieval logic in `apps/api/app/db/postgres.py` (`search_session_memory`) is currently scoped strictly to the provided `session_id` (`project_id`).
- We will update the SQL query to perform a `JOIN` against the `projects` table. This allows the query to find all memories stored across *any* project that shares the same `company_id` as the querying project.
- Query change:
  ```sql
  SELECT sm.id, sm.content, sm.metadata, (sm.embedding <=> $1) as distance
  FROM session_memory sm
  JOIN projects p_target ON sm.project_id = p_target.id
  JOIN projects p_source ON p_source.id = $2
  WHERE p_target.company_id = p_source.company_id
  ORDER BY distance ASC
  LIMIT $3;
  ```
- The mock implementation (for local/test environments) will similarly be updated to filter by matching `company_id` rather than just matching `project_id`.

## Atomic Implementation Steps

**Step 1: Implement "Create New Company" UI (BUG-048)**
- **Files Read:** `apps/web/src/components/global-header.tsx`, `apps/web/src/components/company-provider.tsx`
- **Files Modified:** `apps/web/src/components/global-header.tsx`
- **Action:** Add the "Create New Company" button to the dropdown and implement the modal overlay with a form that calls `createCompany`.

**Step 2: Update Vector Search for Cross-Project Retrieval (BUG-043)**
- **Files Read:** `apps/api/app/db/postgres.py`, `apps/api/tests/test_db.py`
- **Files Modified:** `apps/api/app/db/postgres.py`, `apps/api/tests/test_db.py`
- **Action:** Modify `search_session_memory` (both mock and SQL implementations) to fetch memories across all projects belonging to the same `company_id`. Update `test_db.py` expectations to match the new cross-project retrieval behavior.
