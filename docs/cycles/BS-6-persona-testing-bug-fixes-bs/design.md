# System Design: Persona Testing Bug Fixes (BS-6)

## 1. Overview
This document outlines the design and atomic implementation steps required to fulfill the BS-6 specification. The work addresses the evidence ledger data leak, sanitizer fabrication, cross-project memory gap, UI data-binding for verticals and titles, and markdown rendering issues.

## 2. Architecture & Data Flow Updates
- **Evidence Ledger Data Leak (BUG-053)**: `extract_evidence_ledger_from_messages` will strictly filter input to process only string content from `HumanMessage` objects (or messages where `role == "user"` or `type == "human"`), preventing raw AI tool use outputs and internal `<thinking>` tags from being scanned as user claims.
- **Sanitizer Fabrication (BUG-052)**: The prompt in `_node_sanitize_input` will be updated with explicit negative constraints to prohibit generating first-person text, resolving meta-questions, or hallucinating conversational responses.
- **Cross-Project Memory (BUG-043)**: During new session creation in `/api/v1/orchestrate`, we will query for prior projects belonging to the same `company_id`. We will extract and summarize their established facts (location, tools, constraints) and inject them into `metadata["company_context"]`. The `CONSULTANT_INTAKE_PROMPT` will be updated to consume this context.
- **Header & Title UI (BUG-054 / BUG-045)**: 
  - The `business_vertical` initialization in `main.py` will use `company_industry` rather than hardcoding `"GENERIC"`.
  - The Semantic Project Titles heuristic currently implemented in `create_project` (`/api/v1/projects`) will be extracted into a shared helper function and applied to `/api/v1/orchestrate` to ensure consistent project titles.
- **Markdown Rendering (BUG-055)**: The frontend will add `react-markdown` as a dependency. Components rendering textual report blocks (e.g., in `dual-view-layout.tsx` and `report-view.tsx`) will be updated to use `<ReactMarkdown>` instead of rendering raw string output.

## 3. Atomic Implementation Steps

### Step 1: Fix Evidence Ledger Data Leak (BUG-053) & Sanitizer Fabrication (BUG-052)
- **Read:** `apps/api/app/core/orchestrator.py`
- **Modify:** `apps/api/app/core/orchestrator.py`
  - Update `extract_evidence_ledger_from_messages` to filter `messages` by `role == "user"` / `type == "human"` and ensure content is a string.
  - Update `_node_sanitize_input`'s `CONSULTANT_INTAKE_PROMPT` to add constraints against answering user questions and writing first-person text.

### Step 2: Implement Cross-Project Memory Hydration (BUG-043)
- **Read:** `apps/api/app/main.py`, `apps/api/app/db/postgres.py`, `apps/api/app/core/orchestrator.py`
- **Modify:** `apps/api/app/main.py`, `apps/api/app/core/orchestrator.py`
  - In `main.py` (`/api/v1/orchestrate`), fetch previous `SessionState` for the company and build a brief `company_context` summary. Inject into `SessionState.metadata`.
  - In `orchestrator.py`, update `CONSULTANT_INTAKE_PROMPT` to include `Company Context: {company_context}`.

### Step 3: Fix Project Titles (BUG-045) & Vertical Focus (BUG-054)
- **Read:** `apps/api/app/main.py`
- **Modify:** `apps/api/app/main.py`
  - Extract the `Semantic Project Titles heuristic` into a helper `_generate_semantic_title(raw_text)`. Apply it to both `create_project` and `/api/v1/orchestrate`.
  - In `main.py` (line ~634), initialize `business_vertical=db_vertical` or `company_industry` instead of `"GENERIC"`.

### Step 4: Fix Markdown Rendering (BUG-055)
- **Read:** `apps/web/package.json`, `apps/web/src/components/report-view.tsx`, `apps/web/src/components/dual-view-layout.tsx`
- **Modify:** `apps/web/package.json`, `apps/web/src/components/report-view.tsx`, `apps/web/src/components/dual-view-layout.tsx`
  - Add `react-markdown` to `package.json`.
  - Import and wrap raw LLM string sections in `<ReactMarkdown>` in `report-view.tsx` and `dual-view-layout.tsx`.
