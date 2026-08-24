# System Design: Development Workflow Control Plane

## 1. Design goals

This design defines a reusable workflow control plane in a separate repository and service. The control plane owns requirements, collaboration, phases, artifacts, approvals, executions, evidence, and audit history. BuildSense remains a separate domain application and the first integration client; its domain workflow is not moved into the control-plane codebase.

The first release supports multiple users, teams, projects, and requirements, with direct developer execution as the usable path. Headless execution is represented by a stable adapter boundary but remains disabled until a secure worker exists.

## 2. Architecture

```text
Standalone control-plane Next.js UI
        |
Standalone control-plane FastAPI API
        |
Workflow service + authorization policy
   |            |              |
PostgreSQL   Artifact store   Event stream
   |            |              |
Git/import adapters       Direct/headless execution adapters

BuildSense connector  ───── versioned API/webhook contract ─────┘
```

### 2.1 Source-of-truth boundaries

- PostgreSQL is the source of truth for users, organizations, memberships, teams, projects, work items, phase state, approvals, executions, events, and evidence metadata.
- Git remains the source of truth for source files, branches, commits, and diffs.
- Artifact storage holds bounded snapshots, reports, logs, and imported result files; database rows hold hashes, metadata, and references.
- The existing BuildSense telemetry store remains useful for local diagnostics but is not the durable control-plane event store.
- The control plane must not import BuildSense internals directly. BuildSense integration uses versioned API contracts, webhooks, or a small connector package with explicit domain metadata.
- Generic control-plane migrations, routes, UI, workers, and adapters live in the standalone control-plane repository. BuildSense changes are limited to integration configuration, connector code, and contract tests.

### 2.3 Synchronization boundary

Git is authoritative for source state. The control plane is authoritative for workflow state, ownership, approvals, and collaboration. Neither system should silently overwrite the other.

```text
Requirement / atomic step
        ↓ approved handoff
Repository branch / worktree
        ↓ push, import, polling, webhook, or local bridge
Commits, branches, diffs, pull requests, checks
        ↓ reconciliation
Requirement timeline and evidence status
```

The first release supports manual commit/PR import and bounded polling. Webhooks and a local developer bridge are planned extensions. All synchronization paths write the same normalized commit, file-change, test-result, and event records.

### 2.2 Tenant hierarchy

```text
organization
  └── workspace
        ├── memberships
        ├── teams
        └── projects
              └── work_items
                    ├── phases
                    ├── artifacts
                    ├── executions
                    ├── approvals
                    ├── test_runs
                    └── events
```

The first implementation may provision one default workspace per organization, but the schema and authorization functions must carry organization and workspace scope explicitly.

## 3. Data model

Add control-plane tables to a dedicated migration or schema section:

- `organizations`: tenant identity, status, policy JSON, quotas, timestamps.
- `users`: application identity reference and profile metadata; do not duplicate provider secrets.
- `memberships`: organization/workspace membership, role, invitation status, and timestamps.
- `teams`: organization/workspace team ownership.
- `team_memberships`: team membership and optional team role.
- `projects`: repository metadata, default branch, adapter configuration, and owning workspace.
- `project_teams`: explicit team access to projects.
- `requirements`: user input, normalized title/summary, priority, acceptance criteria, visibility, and revision number.
- `workflow_cycles`: one delivery attempt for a requirement and its overall status.
- `workflow_phases`: phase type, status, owner, ordering, timestamps, and current artifact revision.
- `atomic_steps`: design-defined implementation unit, allowed paths, status, and order.
- `artifacts`: immutable version, type, content reference, hash, source, and linked Git revision.
- `approvals`: artifact version, approval type, actor, role at approval time, decision, and reason.
- `executions`: direct/headless/import/test execution metadata, limits, status, actor, and stop reason.
- `validation_policies`: required test categories, completion rules, exception permissions, and inheritance scope.
- `test_cases`: planned verification, linked acceptance criteria, type, expected outcome, author, provenance, and review state.
- `requirement_test_links`: many-to-many links between requirements/criteria and test cases with required/optional status.
- `test_runs`: command, revision, result summary, duration, and artifact reference.
- `test_case_executions`: test-case-to-run mapping, status, environment, output artifact, and verification provenance.
- `repository_connections`: provider, URL, default branch, tracked branches, sync cursor, webhook status, and adapter configuration.
- `repository_commits`: repository-scoped SHA, branch/ref, author metadata, parent SHAs, message, timestamp, and imported source.
- `commit_file_changes`: commit SHA, path, change type, and size metadata.
- `work_item_commit_links`: requirement/cycle/step to commit relationship, link source, confidence, confirming actor, and timestamp.
- `pull_requests`: provider ID, source/target refs, status, review state, and linked work items.
- `repository_checks`: commit/PR check name, provider, status, conclusion, URL, and imported timestamp.
- `defect_links`: references to existing defect records or imported ledger entries.
- `workflow_events`: append-only, tenant-scoped audit and live-activity records.

Foreign keys must prevent cross-tenant relationships. Row-level security or equivalent service authorization must be applied consistently to every tenant-owned table.

## 4. Workflow state and transitions

The service, not the browser, owns transition validation. Initial transitions are:

```text
draft -> awaiting_approval -> in_progress -> paused
                         \-> blocked / failed / cancelled / completed
```

Phase-specific gates:

- Specification approval is required before design begins.
- Design approval is required before implementation begins.
- An implementation step cannot start unless its parent phase and repository revision are recorded.
- Delivery cannot be marked complete without required validation evidence or an explicit approved exception.
- A requirement cannot be marked complete when a required acceptance criterion has no linked test case or approved validation exception.
- A passing test written only after implementation does not by itself count as independent validation; its provenance must be visible.
- A failed or blocked execution never creates a completed phase implicitly.

Every transition creates a `workflow_events` row with actor type, actor ID, prior state, new state, reason, and related artifact/execution IDs.

## 5. API design

Add a versioned control-plane router, separate from BuildSense’s domain endpoints:

```text
GET/POST   /api/v1/control/organizations
GET/POST   /api/v1/control/workspaces
GET/POST   /api/v1/control/teams
GET/POST   /api/v1/control/projects
GET/POST   /api/v1/control/requirements
GET        /api/v1/control/requirements/{id}
POST       /api/v1/control/requirements/{id}/transitions
GET        /api/v1/control/requirements/{id}/timeline
GET/POST   /api/v1/control/requirements/{id}/approvals
GET/POST   /api/v1/control/requirements/{id}/artifacts
GET/POST   /api/v1/control/requirements/{id}/executions
POST       /api/v1/control/executions/{id}/evidence
GET        /api/v1/control/projects/{id}/summary
GET/POST   /api/v1/control/projects/{id}/repository/sync
GET        /api/v1/control/projects/{id}/repository/commits
POST       /api/v1/control/projects/{id}/repository/import
POST       /api/v1/control/repository/webhooks/{provider}
GET/POST   /api/v1/control/requirements/{id}/test-cases
POST       /api/v1/control/test-executions
```

All endpoints resolve the current user server-side and validate organization, workspace, team, project, and work-item access. Client-provided tenant IDs are lookup hints only, never authorization evidence.

BuildSense integration uses a separate connector surface, for example:

```text
POST /api/v1/integrations/buildsense/projects
POST /api/v1/integrations/buildsense/events
POST /api/v1/integrations/buildsense/evidence
```

The connector translates BuildSense-specific project/session/evaluation concepts into generic project, requirement, execution, artifact, and test evidence contracts. It must not expose BuildSense database credentials or require the control plane to query BuildSense tables directly.

## 6. Direct execution design

Direct execution is a guided handoff, not remote command execution.

The API creates an execution record with `mode=direct` and returns a bounded handoff containing:

- requirement and approved artifact references;
- exact atomic step and allowed paths;
- repository and base revision;
- validation commands;
- policy constraints;
- a correlation ID for imported evidence.

The UI renders a copyable prompt and status controls. Evidence import accepts commit IDs, branch names, changed-file metadata, test summaries, and bounded logs. The server verifies repository ownership and attempts to resolve commits against the configured remote before accepting them as linked evidence.

The UI must label direct evidence as `user_reported` or `imported` unless a trusted local bridge provides execution events.

## 7. Repository synchronization and status reconciliation

### 7.1 Correlation identifiers

Each work item and atomic step receives a stable identifier. Direct handoffs and headless execution contexts include these identifiers in the recommended branch name, commit trailer, and pull request description:

```text
Workflow-Requirement: REQ-104
Workflow-Cycle: CYCLE-22
Workflow-Step: STEP-03
```

The importer first uses explicit trailers or trusted execution context, then branch and pull-request conventions, and finally allows a user to confirm a proposed link. Ambiguous commits remain unlinked instead of being guessed into a requirement.

### 7.2 Synchronization paths

- **Manual import:** user supplies a commit SHA, branch, pull request, test result, or repository URL. The adapter verifies the reference and records provenance.
- **Polling:** a project-scoped sync job reads new commits, refs, pull requests, and repository checks after the last cursor. Polling is bounded and idempotent.
- **Webhook:** a later provider adapter accepts signed push, pull-request, and check-run events and queues reconciliation rather than performing heavy work inside the request.
- **Local bridge:** a future developer-side command reports branch, commit, changed files, commands, exit codes, and tests for direct mode.
- **Headless worker:** the execution adapter creates and owns the worktree context, so commits and tests can be linked automatically with `platform_observed` provenance.

All paths must be idempotent by provider event ID or repository/commit SHA. Replaying an event must not create duplicate commits, test runs, or links.

### 7.3 Completion rules

The existence of a commit never marks a requirement complete by itself. Reconciliation calculates evidence fields such as:

- commit found;
- expected files changed;
- targeted tests passed;
- CI checks passed;
- review completed;
- acceptance criteria confirmed;
- delivery decision recorded.

The UI may derive a suggested status such as `awaiting_review`, but only a valid workflow transition or configured automation may mark a requirement `completed`. Every derived status stores its evidence and rule version.

### 7.4 Unlinked change queue

Repository changes that cannot be confidently linked appear in an authorized project-level unlinked-change queue. A reviewer may link or dismiss them, and that decision is recorded as an event. The system must never hide an imported repository change merely because it lacks a requirement link.

### 7.5 Evidence provenance

Every imported commit, test, pull request, and check records one of:

- `platform_observed`;
- `repository_imported`;
- `user_reported`;
- `agent_reported`.

The UI must make this provenance visible and must not present user-reported direct-mode evidence as if the platform executed or independently verified it.

### 7.6 Test and validation evidence

Tests are part of delivery, not merely reporting. The system preserves the distinction between an acceptance criterion, a planned test case, the test implementation in source control, a test execution at a known revision, and an independent review or approved exception.

Required test cases are derived from approved acceptance criteria or explicit invariants. Test provenance identifies whether a test was pre-existing, developer-authored, agent-authored, generated from the specification, or independently reviewed. A validation policy may require unit, integration, API, UI, security, performance, or evaluation categories. A requirement may only complete when all required links have passing evidence or an authorized exception.

## 8. Headless execution adapter

Define an interface such as:

```text
start(execution_context) -> execution_id
stream(execution_id) -> sanitized events
pause(execution_id)
cancel(execution_id)
resume(execution_id)
```

The MVP supplies an unavailable adapter that returns a clear capability error. No fake execution records or synthetic completion events are allowed. A later worker must use isolated worktrees, allowlisted commands, secret-boundary controls, budgets, cancellation, and human approval gates.

## 9. Import and reconciliation

The importer reads existing BuildSense evidence and creates traceable records:

- `docs/cycles/index.json` becomes historical cycle metadata.
- Archived cycle `spec.md` and `design.md` files become immutable artifacts.
- Git history supplies commits, changed files, branches, and commit relationships.
- `docs/DEFECT_LEDGER.md` becomes linked defect evidence where a direct mapping is possible.
- Existing pytest/evaluation outputs become test or evaluation evidence with an explicit source and revision confidence.
- Existing local telemetry is imported only when the event payload is privacy-safe and has a stable run identifier.

The same reconciliation code handles ongoing repository sync. Historical cycle import and live commit sync must produce the same normalized artifact and link shapes.

The initial BuildSense import may be run from the control-plane repository against an explicitly selected BuildSense checkout, but the resulting integration must be replaceable by the versioned connector. This prevents the generic product from becoming coupled to BuildSense’s filesystem layout or internal schema.

Importer decisions must be recorded as events. Unknown mappings remain unknown instead of being guessed as completed implementation steps.

## 10. Frontend information architecture

Add a protected workflow area:

```text
/[lang]/workflow
  /organizations
  /teams/[teamId]
  /projects/[projectId]
  /projects/[projectId]/requirements
  /requirements/[requirementId]
```

The requirement detail page is the primary experience:

- Header: title, project, team, owner, status, priority, next action.
- Timeline: intake, spec, approvals, design, implementation, tests, review, delivery.
- Artifacts: readable spec/design, diffs, reports, logs, and hashes.
- Execution: direct handoff, evidence import, or headless capability status.
- Activity: user, agent, integration, and system events filtered by permission.
- Collaboration: assignees, reviewers, watchers, blockers, and comments only where necessary for workflow decisions.
- Repository evidence: linked commits, changed files, pull requests, checks, sync freshness, and unlinked changes.

Start with organization, team, project, and requirement pages. Avoid building a full chat, sprint board, or generic issue-management interface.

## 11. Authorization model

Centralize authorization in a service/policy module. Required checks include:

- organization membership for every organization-scoped operation;
- workspace membership for workspace access;
- project/team membership for project and requirement access;
- role permission for approvals, policy changes, imports, and execution controls;
- immutable approval eligibility evaluated at approval time;
- event visibility filtered by the same tenant scope as the related entity.

Use server-side policy tests for allowed and denied access across two organizations, two workspaces, and multiple roles.

## 12. Atomic Implementation Steps

Each step is intentionally limited to at most four source files in context. Paths below are exact paths to read or modify.

### Step 1: Add control-plane schema and tenant primitives

Read: `apps/api/app/db/schema.sql`, `apps/api/app/core/auth.py`, `apps/api/app/core/config.py` in the new control-plane repository.

Modify: `apps/api/app/db/schema.sql`, `apps/api/app/core/auth.py`, `apps/api/app/core/config.py`, `apps/api/tests/test_db.py` in the new control-plane repository.

Create organizations, workspaces, memberships, teams, projects, requirements, cycles, phases, artifacts, approvals, executions, test runs, and events with tenant-safe constraints and policy configuration.

### Step 2: Add typed control-plane and validation models/repositories

Read: `apps/api/app/models/state.py`, `apps/api/app/db/postgres.py`, `apps/api/app/db/schema.sql`.

Modify: `apps/api/app/models/state.py`, `apps/api/app/db/postgres.py`, `apps/api/tests/test_db.py`, `apps/api/tests/test_ontology.py`.

Add Pydantic contracts and repository methods for requirements, cycles, phases, artifacts, approvals, executions, validation policies, test cases, and test evidence.

### Step 3: Add centralized authorization policies

Read: `apps/api/app/core/auth.py`, `apps/api/app/db/postgres.py`, `apps/api/app/core/config.py`.

Modify: `apps/api/app/core/auth.py`, `apps/api/app/db/postgres.py`, `apps/api/tests/test_companies.py`, `apps/api/tests/test_db.py`.

Implement organization/workspace/project role checks and cross-tenant denial tests.

### Step 4: Add workflow transition service and durable events

Read: `apps/api/app/models/state.py`, `apps/api/app/db/postgres.py`, `apps/api/app/telemetry/logging.py`.

Modify: `apps/api/app/models/state.py`, `apps/api/app/db/postgres.py`, `apps/api/app/telemetry/logging.py`, `apps/api/tests/test_resilience.py`.

Implement validated transitions, immutable approval links, append-only workflow events, explicit blocked/failed states, required-test gates, and approved validation exceptions.

### Step 5: Add control-plane API routes

Read: `apps/api/app/main.py`, `apps/api/app/core/auth.py`, `apps/api/app/db/postgres.py`, `apps/api/app/models/state.py`.

Modify: `apps/api/app/main.py`, `apps/api/app/core/auth.py`, `apps/api/app/db/postgres.py`, `apps/api/tests/test_companies.py`.

Expose organization, team, project, requirement, artifact, approval, execution, timeline, and summary endpoints with authorization.

### Step 6: Add repository connection and Git synchronization primitives

Read: `scripts/archive_checkpoint.py`, `docs/cycles/index.json`, `apps/api/app/db/postgres.py`, `apps/api/app/core/config.py` in the control-plane repository, plus the selected BuildSense archive through the importer boundary.

Modify: `scripts/archive_checkpoint.py`, `apps/api/app/db/postgres.py`, `apps/api/app/core/config.py`, `apps/api/tests/test_db.py` in the control-plane repository.

Add repository connections, idempotent commit/ref/check records, sync cursors, explicit commit-link provenance, and historical BuildSense cycle import without inventing missing source-commit relationships.

### Step 7: Add repository sync API and reconciliation status

Read: `apps/api/app/main.py`, `apps/api/app/db/postgres.py`, `apps/api/app/models/state.py`, `apps/api/app/core/config.py`.

Modify: `apps/api/app/main.py`, `apps/api/app/db/postgres.py`, `apps/api/app/models/state.py`, `apps/api/tests/test_resilience.py`.

Expose manual import and project sync endpoints, commit-to-requirement linking, unlinked-change handling, evidence provenance, and non-automatic completion status.

### Step 8: Add test-plan and validation evidence APIs

Read: `apps/api/app/main.py`, `apps/api/app/db/postgres.py`, `apps/api/app/models/state.py`, `apps/api/app/core/config.py`.

Modify: `apps/api/app/main.py`, `apps/api/app/db/postgres.py`, `apps/api/app/models/state.py`, `apps/api/tests/test_resilience.py`.

Expose test-case creation/linking, validation-policy lookup, test-result import, provenance recording, independent-review state, and completion-gate evaluation.

### Step 9: Add direct execution handoff and evidence import

Read: `apps/api/app/main.py`, `apps/api/app/db/postgres.py`, `apps/api/app/models/state.py`, `apps/api/app/core/config.py`.

Modify: `apps/api/app/main.py`, `apps/api/app/db/postgres.py`, `apps/api/app/models/state.py`, `apps/api/tests/test_resilience.py`.

Create direct-mode execution records, bounded handoffs, evidence submission, commit association, and explicit user-reported/imported provenance.

### Step 10: Add headless adapter placeholder

Read: `apps/api/app/main.py`, `apps/api/app/models/state.py`, `apps/api/app/core/config.py`.

Modify: `apps/api/app/main.py`, `apps/api/app/models/state.py`, `apps/api/app/core/config.py`, `apps/api/tests/test_resilience.py`.

Expose a capability-aware placeholder that cannot claim execution or completion while preserving the future adapter contract.

### Step 11: Add workflow frontend shell and requirement detail view

Read: `apps/web/src/app/[lang]/layout.tsx`, `apps/web/src/lib/api.ts`, `apps/web/src/components/global-header.tsx`, `apps/web/src/components/ui/card.tsx`.

Modify: `apps/web/src/app/[lang]/layout.tsx`, `apps/web/src/lib/api.ts`, `apps/web/src/components/global-header.tsx`, `apps/web/src/components/ui/card.tsx`.

Add navigation and shared UI primitives for workflow pages without changing the existing BuildSense product flow.

### Step 12: Add project, requirement list, timeline, repository, and test evidence UI

Read: `apps/web/src/app/[lang]/projects/[id]/page.tsx`, `apps/web/src/components/strategic-progress.tsx`, `apps/web/src/components/report-view.tsx`, `apps/web/src/lib/api.ts`.

Modify: `apps/web/src/app/[lang]/projects/[id]/page.tsx`, `apps/web/src/components/strategic-progress.tsx`, `apps/web/src/components/report-view.tsx`, `apps/web/src/lib/api.ts`.

Implement the first user-visible tracker views and direct handoff/evidence controls.

### Step 13: Add independent validation and import verification

Read: `apps/api/tests/test_db.py`, `apps/api/tests/test_resilience.py`, `apps/api/tests/test_telemetry.py`, `apps/web/package.json`.

Modify: `apps/api/tests/test_db.py`, `apps/api/tests/test_resilience.py`, `apps/api/tests/test_telemetry.py`, `apps/web/package.json`.

Cover multi-tenant authorization, phase gates, required-test gates, test provenance, sync idempotency, commit linking, unlinked changes, importer behavior, direct/headless distinction, and frontend type/lint validation.

## 13. Verification matrix

| Area | Evidence |
| --- | --- |
| Multi-user isolation | API tests with two organizations and denied cross-tenant reads/writes |
| Roles and approvals | Policy tests showing reviewer approval and viewer/contributor denial |
| Workflow state | Transition tests for approval gates, blocked, failed, paused, and completed states |
| Test traceability | Acceptance-criterion links, required/optional policies, provenance, result import, and independent-review tests |
| Traceability | Requirement-to-commit and commit-to-requirement importer tests |
| Repository sync | Idempotent polling/import tests, commit-link provenance, check-run reconciliation, and unlinked-change visibility |
| Direct execution | Handoff and evidence provenance tests |
| Headless placeholder | Capability error and no-false-completion tests |
| Frontend | Type-check, lint, and browser verification of project/requirement/timeline views |
| Privacy | Secret redaction and bounded artifact/event tests |
| Existing product | Existing BuildSense backend tests and UI smoke checks |

## 14. Risks and mitigations

- **Scope creep into a project-management suite:** keep requirements and delivery evidence central; defer chat, sprints, and broad planning.
- **False confidence from imported evidence:** label provenance and retain confidence/verification status.
- **Direct-mode observability gap:** add a future local bridge, but never imply observation from manual status alone.
- **Headless security exposure:** keep the adapter disabled until isolation, command policy, secrets, budgets, and cancellation are implemented.
- **Cross-tenant leakage:** centralize authorization, use database constraints/RLS, and test negative paths explicitly.
- **Concurrent edits:** version requirements and artifacts; require conflict resolution before approval.
- **Existing BuildSense coupling:** use control-plane adapters and separate routes/models rather than embedding generic entities in domain-specific state.
- **Repository coupling:** keep the control plane in a standalone repository and validate the BuildSense connector through contract fixtures and integration tests.
- **False completion from commits:** require test, review, acceptance, and delivery evidence; make inferred status explainable.
- **Missed or duplicated repository events:** use sync cursors, provider event IDs, commit SHA uniqueness, retry-safe jobs, and visible sync freshness.
- **Direct-mode reporting gap:** distinguish imported and user-reported evidence from platform-observed execution.
