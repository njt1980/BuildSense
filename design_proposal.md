# Design Proposal: Multi-Tenant Data Hierarchy & Chat-First Routing

This document details the architectural updates and implementation plan to enforce a pure, chat-first experience backed by a Multi-Tenant Data Hierarchy (User -> Company -> Project) while deprecating the legacy onboarding wizard.

---

## 1. Relational Data Model & Migrations (Backend)

### Database Changes
We will update the `companies` table to include the `industry_vertical` column, aligning with standard requirements while preserving the existing `industry` column to ensure backward compatibility.

```sql
-- Migration block executed automatically on startup
ALTER TABLE companies ADD COLUMN IF NOT EXISTS industry_vertical VARCHAR(255);

-- Synchronize data for existing records
UPDATE companies SET industry_vertical = industry WHERE industry_vertical IS NULL;
```

The relation hierarchy is defined as:
- **`users`**: Root tenant (managed via Supabase Auth).
- **`companies`**: Linked to `users` (1-to-Many).
- **`projects`**: Linked to `companies` (1-to-Many) via `company_id`.

### LangGraph System Prompt Injection
In `apps/api/app/core/orchestrator.py`, we will dynamically load the active company's details from the database during the pipeline run:

```python
# Inside run_pipeline:
company = await self.db.get_company(project["company_id"])
state.company_name = company["name"]
state.company_industry = company["industry_vertical"]
state.company_core_tools = company["core_tools"]
```

This context is then automatically formatted and appended to `system_prompt_blocks` for every LLM call, ensuring that all agent reasoning is grounded in the company's tool stack and industry.

---

## 2. API Route Security (Backend)

To prevent cross-tenant information leaks, we will enforce strict ownership checks on all project and orchestration requests. 

When a user POSTs to `/api/v1/projects` or `/api/v1/orchestrate` with a `company_id`, the backend will perform the following validation:

```python
company = await postgres_client.get_company(payload.company_id)
if not company or company["user_id"] != current_user.id:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied to the specified company."
    )
```

---

## 3. Next.js Frontend State & Context Switching (Frontend)

### Global Context Provider
We will implement `CompanyProvider` in `apps/web/src/components/company-provider.tsx` to handle:
- Fetching and storing all companies belonging to the user.
- Tracking the currently selected `activeCompany`.
- Persisting the selection in `localStorage`.

All dashboard widgets, workspace tables, and prompt intake templates will consume this context.

### Lightweight Onboarding / "Create Company" Flow
- If a user logs in and the API returns 0 companies, the page will render a fullscreen `CreateCompanyFlow` instead of the main dashboard.
- Access to the dashboard is blocked until at least one company baseline is established.

### Global switcher UI
We will build a global `Header` containing a styled dropdown switcher for selecting the active company.
- On the home page: Selecting a new company instantly filters the projects list.
- On the workspace page: If a user switches the company context, they are redirected back to the home page (`/[lang]`) under the new company's context.

---

## 4. Deprecation of Onboarding Wizard (Frontend)

We will remove the conditional `if (isOnboardingActive)` layout from `/[lang]/projects/[id]/page.tsx` entirely. 
- The user will land directly in the workspace interface.
- The default tab selection will be set to the **Dialogue Panel** (Chat).
- The manual "Role Persona" selection form is removed; the backend will default this to `"Solo Founder"`.

---

## 5. Seamless Chat-First Routing (End-to-End)

### Route 1: Home Page Discovery Prompt
1. The user types a business process prompt on the home page and clicks **Start Discovery**.
2. The UI enters a full-screen loading overlay.
3. The frontend calls `POST /api/v1/orchestrate` passing the initial prompt and the active `company_id`.
4. The backend creates the project, runs the LangGraph orchestrator's initial loop, saves the resulting messages (user prompt + AI's clarifying response), and returns the state.
5. The frontend redirects the user directly to `/[lang]/projects/[projectId]`. Since the chat history is pre-populated, they see the initial dialogue rendered instantly with no flicker or intermediate wizard forms.

### Route 2: New Blank Project
1. The user clicks **➕ New Blank Project** in the dashboard.
2. The UI enters a loading state.
3. The frontend calls `POST /api/v1/projects` with a placeholder title and the active `company_id`.
4. The backend creates the project.
5. The frontend redirects to `/[lang]/projects/[projectId]`.
6. When the workspace mounts and fetches the session state, the backend notices the chat history is empty. It automatically initializes a default greeting:
   > *"Hello! I am BuildSense, your AI operations analyst. Let's work together to map and optimize your workflows at **[Company Name]**. To get started, describe a manual workflow..."*
7. The greeting renders immediately in the Dialogue Panel.

---

## 6. Verification and Rollout Plan

1. **Backend Tests**: Run `pytest` to verify RLS configurations and endpoint status.
2. **Security Verification**: Attempt to create a project using a company ID belonging to a different user, asserting a `403 Forbidden` response.
3. **Manual Walkthrough**: Test the end-to-end user flows for both a new company creation, discovery prompt execution, and blank workspace creation.
