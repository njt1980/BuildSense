# Specification: Development Workflow Control Plane

## 1. Objective

Build a reusable, project-agnostic platform that captures a software or technical requirement and makes the full path from requirement through specification, design, implementation, testing, review, and delivery visible to a human user.

BuildSense will be the first dogfooding project, but the platform must not depend on BuildSense-specific concepts such as SMB workflow optimization, LangGraph, or a particular agent prompt.

## 2. Product outcomes

The platform must let a user answer, at any time:

- What requirements were submitted?
- What is the current status of each requirement?
- What specification and design were produced?
- Who or what approved each phase?
- What code, commits, branches, and files changed?
- Which tests and evaluations ran, and what were their results?
- What is blocked, failed, awaiting input, or incomplete?
- What did the agent do, and what decisions did it make?
- What was ultimately delivered versus originally requested?
- Which team or organization owns the work?
- Which users can view, approve, execute, or administer it?

## 3. Scope

### 3.1 MVP in scope

- Create and manage organizations, teams, projects, and requirements/work items.
- Support multiple users working in the same workspace with explicit membership and role permissions.
- Support organization-owned teams, repository-backed coding projects, and multiple requirements per project without mixing their visibility or audit history.
- Associate a work item with a repository and project.
- Track a standard workflow: intake, specification, design, implementation, validation, review, and delivery.
- Store phase status, timestamps, owners, dependencies, blockers, and human decisions.
- Link phases to durable artifacts, Git commits, branches, diffs, test runs, evaluation results, and defect records.
- Define required validation before implementation and capture test cases, test implementations, executions, and results linked to acceptance criteria.
- Provide a web interface with a work-item list, detail page, phase timeline, artifact viewer, activity history, and approval controls.
- Import and reconcile existing Git history, root/cycle specification files, archived cycles, test results, and defect-ledger entries.
- Stream agent execution events and show captured stdout/stderr summaries, changed files, proposed diffs, costs, and stop reasons.
- Require explicit human approval before moving from specification to design and from design to implementation.
- Record the acting user separately from the assigned owner, requesting user, approving user, and executing agent.
- Preserve an append-only activity and audit history across all user, agent, system, and integration actions.
- Support statuses including `draft`, `awaiting_input`, `awaiting_approval`, `in_progress`, `paused`, `blocked`, `failed`, `completed`, and `cancelled`.
- Enforce per-run step, time, token, and spend limits.
- Support direct developer execution as the first usable execution mode: users can take an approved atomic step to Claude Code, Codex, or another local coding agent and report/import the resulting evidence.
- Define a headless execution mode through an adapter contract, but keep its worker implementation disabled or placeholder-only in the MVP.

### 3.2 Extensibility in scope

- Agent-runner adapters for Claude Code, Codex, and compatible CLI/API agents. Direct mode and headless mode must share the same work-item, step, evidence, and status contracts.
- Repository adapters beginning with local Git repositories and GitHub-compatible remotes.
- Test adapters beginning with shell commands, pytest, npm scripts, and CI result ingestion.
- Project adapters that add domain-specific phases, prompts, fields, evaluators, and UI panels without modifying the core workflow engine.
- Event and artifact schemas that remain stable across adapters.

## 4. Explicit non-goals for the MVP

- Fully autonomous production deployment.
- Direct execution of arbitrary commands from the browser.
- Automatic merging to a protected default branch.
- Replacing Git, GitHub, GitLab, or a CI system as the source of truth for source code.
- Treating generated tests as independent proof of correctness without review or separately sourced assertions.
- Production-scale observability, billing, or enterprise identity management.
- Enterprise SSO, SCIM provisioning, complex organizational hierarchies, and advanced compliance exports in the first release; the tenancy model must remain extensible for them.
- Supporting every agent, repository host, or CI provider in the first release.

## 5. Canonical workflow

Every work item follows an auditable state machine:

1. **Intake** — capture the user requirement, context, priority, constraints, and acceptance intent.
2. **Specification** — produce a precise scope, non-goals, requirements, and acceptance criteria.
3. **Specification approval** — obtain explicit human approval or record requested changes.
4. **System design** — produce architecture, data flow, risks, and atomic implementation steps.
5. **Design approval** — obtain explicit human approval before source changes.
6. **Implementation** — execute one atomic step at a time in an isolated branch/worktree.
7. **Validation** — run targeted tests, static checks, integration checks, and optional evaluations.
8. **Review** — present diffs and evidence for human or independent-agent review.
9. **Delivery** — record final commits, remaining limitations, deployment state, and outcome.

Phase transitions must be recorded as events and must include the actor, reason, timestamp, and related artifact or approval where applicable.

## 6. Functional product model

The primary navigation and ownership model is:

```text
Organization
  ├── Users, memberships, roles, and policies
  ├── Teams
  │     └── Coding projects
  │             └── Requirements / work items
  │                     └── Spec → Design → Code → Tests → Delivery
  └── Organization-level budgets and integrations
```

A project is a durable container for a repository, shared team context, policies, and multiple requirements. A requirement is the unit that moves through the specification-to-delivery workflow. A team may own multiple projects, and a project may have more than one authorized team where collaboration is explicitly granted.

The MVP must support these core user journeys:

1. An organization lead creates a team, adds members, and creates a repository-backed coding project.
2. A team member submits a requirement inside the project and tracks its status independently of other requirements.
3. A reviewer opens the requirement, reads the exact specification or design artifact, and approves or requests changes.
4. A developer selects direct execution, receives the approved atomic step and context, completes work in their local agent, and imports or records commits and test evidence.
5. The project and team views summarize active, blocked, awaiting-approval, and completed requirements without hiding requirement-level detail.
6. A future headless mode can execute the same approved step through a controlled worker without changing the user-facing workflow model.

The platform must not become a general project-management replacement in the MVP. Planning, discussion, and notifications should support the delivery workflow without expanding into full issue tracking, sprint planning, chat, or resource management.

## 7. Core entities

The system must provide durable records for:

- **Organization** — tenant boundary, plan/quotas, security policy, and billing ownership.
- **User** — authenticated human identity and profile; authentication provider details must remain separate from workflow records.
- **Team** — a group within an organization that can own work and receive notifications.
- **Membership** — the relationship between a user and organization/team, including role, status, and invitation history.
- **Workspace** — a collaboration boundary containing projects, requirements, policies, and activity.
- **Project** — repository, adapter configuration, people, policies, and environment metadata.
- **Requirement** — original user input, normalized summary, priority, acceptance criteria, revisions, and visibility scope.
- **Workflow cycle** — one attempt to deliver a requirement, including its phase state and overall outcome.
- **Phase** — one standard or project-defined workflow stage.
- **Atomic step** — a narrowly scoped implementation unit with declared input and output files.
- **Artifact** — specification, design, diff, report, log summary, test result, evaluation, or other evidence.
- **Execution** — one agent, test, import, or validation run with status, limits, costs, and captured evidence.
- **Test case** — a planned verification with purpose, type, expected outcome, provenance, and linked acceptance criteria.
- **Test execution** — one invocation of a test case or validation command at a specific repository revision and environment.
- **Validation policy** — project or workspace rules defining required test categories, approval requirements, and completion gates.
- **Approval** — a human decision tied to an exact artifact version or commit.
- **Defect** — a failure, regression, policy issue, or discovered gap linked to requirements and evidence.
- **Event** — append-only lifecycle record used for audit, activity history, and live updates.

Every organization-owned record must carry an organization and workspace scope, either directly or through a validated parent relationship. Git commit IDs, file paths, hashes, and branch names must be stored as references. Large logs and artifacts must be stored through a bounded artifact store, not embedded indefinitely in workflow state.

## 8. Collaboration and access control

- A user may belong to multiple organizations and workspaces.
- A workspace may contain multiple teams and projects.
- Access must be denied by default and granted through explicit membership, project assignment, or a documented share.
- The initial role model must include at least `organization_admin`, `workspace_admin`, `contributor`, `reviewer`, and `viewer`.
- Only authorized reviewers may approve a specification or design. The approval policy must be configurable per workspace or project.
- A user may be an observer, requester, owner, reviewer, or executor without those responsibilities being conflated.
- Work-item ownership, assignment, watchers, and notification preferences must be separate concepts.
- Users must be able to see who changed a requirement, phase, artifact, approval, permission, or execution setting.
- Concurrent edits to requirements, specifications, designs, and workflow metadata must use versioning or conflict detection; the system must not silently overwrite another user’s changes.
- Approval must reference an immutable artifact version and the approving user’s membership at the time of approval.
- Team-visible activity must exclude secrets, private credentials, and content outside the viewer’s authorized scope.
- Organization-level policies must be able to restrict agent types, repositories, commands, model providers, budgets, retention, and external integrations.
- Notifications for assignment, approval requests, failures, blockers, and completion must be scoped to authorized recipients.

## 9. Agent execution requirements

### 9.1 Direct developer execution

- Direct mode is the first supported execution path.
- The platform presents the approved requirement, design, atomic step, file scope, constraints, and validation commands in a developer handoff view.
- The user may copy the handoff into a local coding agent or use a future local bridge/CLI.
- The user or bridge must report the branch, commits, changed files, tests, failures, and final status back to the platform.
- Direct mode must clearly label evidence as user-reported or imported rather than implying that the platform observed the local execution.
- Imported commits and tests must be checked against the expected repository and revision where possible.

### 9.2 Headless execution placeholder

- The system must expose an execution-mode abstraction with `direct` and `headless` values.
- The MVP may display headless mode as unavailable or invite-only; it must not claim that a headless run occurred when no worker executed it.
- The future headless adapter must receive the same approved atomic step used by direct mode and return the same evidence contract.
- Enabling headless mode later must not require a second workflow, approval model, or traceability system.

- Agents run only through a server-side worker using an isolated worktree or equivalent sandbox.
- The worker receives a declared work item, phase, atomic step, allowed files, repository revision, requesting user, acting organization/workspace, and applicable policies.
- The worker must not bypass approval gates, alter protected branches, or expand file scope silently.
- Every command, tool call, model call, file change, test result, retry, and stop condition must produce a sanitized event.
- Secrets must be injected only at execution boundaries and must never be written to the UI, Git, artifacts, or telemetry.
- The worker must stop and mark the execution `awaiting_input` or `blocked` when requirements are ambiguous, approval is missing, limits are reached, or a safety policy is violated.
- Retry policies must be bounded and visible.
- A failed execution must preserve its worktree diff and evidence for inspection without automatically presenting it as delivered code.

## 10. Traceability requirements

The system must support bidirectional navigation:

- Requirement → specification → design → atomic step → commit → test/evaluation → delivery.
- Commit/file/test/defect → the requirement and phase that caused it.

The tracker must distinguish:

- planned versus implemented requirements;
- changed versus unchanged files;
- passed versus merely executed tests;
- agent-generated evidence versus independently reviewed evidence;
- completed work versus work that only has a passing local check;
- current repository state versus historical execution state.

Tests are part of delivery, not merely reporting. Required test cases must be derived from approved acceptance criteria or explicit invariants. Test provenance must identify whether a test was pre-existing, developer-authored, agent-authored, generated from the specification, or independently reviewed. Completion gates must support unit, integration, API, UI, security, performance, and evaluation categories.

## 11. Security and governance

- Multi-tenant records must be isolated by organization, workspace, project, and user according to the access-control model.
- Every read and write path must validate tenant scope server-side; client-provided organization, workspace, or project IDs must never be trusted by themselves.
- Browser clients must not receive raw secrets, unrestricted command output, or unbounded model/tool payloads.
- Destructive commands, external writes, deployment actions, and protected-branch operations require explicit policy and approval.
- Human approvals must be tied to immutable artifact versions, not just a mutable phase label.
- The platform must support cancellation, pause, resume, and forced termination of agent runs.
- All execution limits and policy decisions must be visible in the audit trail.
- Organization and workspace quotas must be enforced for concurrent runs, agent spend, retained artifacts, and repository integrations.
- Deactivated users must lose access without deleting the historical audit trail or invalidating completed approvals.
- The system must support export and deletion policies that distinguish user data, organization records, source references, and immutable audit evidence.

## 12. Acceptance criteria

The MVP is acceptable when:

1. A user can submit a requirement and see it as a tracked work item.
2. A work item displays the current phase, status, owner, blockers, and next action.
3. The user can inspect the exact specification and design artifacts associated with the work item.
4. The system records approvals against exact artifact versions.
5. Implementation steps show changed files, commits, diffs, and execution status.
6. Test and evaluation runs show command, revision, start/end time, status, summarized output, and linked evidence.
7. The user can trace from a requirement to delivered commits and back from a commit to its requirement.
8. An agent run can pause for approval or input and resume from the last durable checkpoint.
9. A failed or blocked run is clearly distinguished from a completed run.
10. Existing BuildSense cycles can be imported without losing their Git, spec, design, approval, test, or defect references.
11. The system enforces configured time, step, token, and spend limits.
12. No raw secrets or unbounded external payloads appear in user-visible artifacts or events.
13. Two authorized users can work in the same workspace while preserving attribution for every action.
14. An unauthorized user cannot view or mutate another organization’s work items, artifacts, executions, approvals, or events.
15. Role permissions prevent a viewer or contributor from approving a phase unless explicitly configured to do so.
16. Concurrent edits produce a visible conflict or version choice rather than silent data loss.
17. Organization and workspace policies can constrain agent execution and budgets.
18. An organization lead can create multiple teams and multiple repository-backed projects.
19. A project can contain multiple independently tracked requirements.
20. Direct execution provides a complete, clearly labeled developer handoff and supports evidence import.
21. Headless execution is represented in the data model without being falsely presented as available or executed in the MVP.
22. Each acceptance criterion can be linked to one or more planned test cases or an approved validation exception.
23. Test executions record repository revision, command, environment, result, duration, provenance, and evidence.
24. A requirement cannot be marked complete when required validation is missing, failing, or only represented by an unreviewed agent-authored test.

## 13. Initial implementation boundary

The first implementation should deliver a read/write workflow tracker and importer over the existing BuildSense repository. It should support one organization with multiple users, teams, projects, and requirements, plus direct developer execution handoff and evidence import. It should not begin with autonomous code modification. Headless execution should remain an adapter placeholder until requirement, artifact, approval, event, and traceability records are working and reviewable.

## 14. Open product decisions

- Whether the first durable store is PostgreSQL-only or PostgreSQL plus object storage.
- Whether the first release supports invitations by email and organization-level role management, or uses pre-provisioned users.
- Whether authentication begins with Supabase Auth or an identity-provider-neutral interface.
- Whether workspace-level approval policies are sufficient initially or team-specific policies are needed.
- Whether required validation policies are inherited from the organization, workspace, project, or a combination with explicit precedence.
- Whether test execution is initially imported from CI/local reports or also run by a platform-owned worker.
- Whether approvals use application identity, Git notes, pull-request reviews, or both.
- Whether the first agent adapter invokes a local CLI or a remote execution service.
- Which repository provider is supported after local Git.
- Whether project-specific workflow definitions are configuration files, database records, or signed plugins.
- Which evidence types are retained permanently versus summarized and expired.
