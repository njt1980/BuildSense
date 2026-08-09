# Product Requirements Document (PRD): BuildSense

## 1. Executive Summary & Vision
**BuildSense** is an agentic AI intelligence engine designed to act as an on-demand product architect, market researcher, educational mentor, and operational consultant. 

Unlike traditional LLM wrappers that dump generic text, BuildSense uses an orchestrated **Router -> Planner -> Executor** pipeline powered by the **Model Context Protocol (MCP)**. It delivers plain-English, actionable intelligence with a dual-output model (Quick Read vs. Deep Dive), catering to both revenue-driven founders and hobbyist developers looking to build for fun or learning.

---

## 2. Core Modes & Motivation Adaptations

BuildSense operates across three functional modes, adapted dynamically by the user's primary motivation:

### 2.1 The Motivation Dual-Engine
At intake, the user selects their primary objective:
1. 💰 **Revenue & Growth:** Focuses on market gaps, commercial defensibility, unit economics, and monetization.
2. 🧠 **Educational / Fun:** Focuses on skill building, project uniqueness, portfolio value, and zero-cost free-tier architectures.

### 2.2 Functional Modes
* **Mode 1: Idea Suggester:** Generates 3 validated concepts tailored to target tech stacks or market niches.
* **Mode 2: Idea Evaluator:** Audits a raw concept across a 4-Pillar Framework (adapted by motivation).
* **Mode 3: Workflow Optimizer:** Deconstructs manual business processes/SOPs and outputs a step-by-step AI modernization roadmap.

---

## 3. End-to-End Pipeline & User Experience

1. **Routing Phase:** Classifies intent into Mode 1, 2, or 3, and assesses prompt completeness.
2. **Human-in-the-Loop (HITL) Clarification:** If the input lacks critical parameters, the system pauses *before* running heavy tools and presents 2–3 interactive, plain-English questions.
3. **Planning Phase:** Generates a deterministic step-by-step task plan (DAG) assigned to specialized worker agent personas.
4. **Execution Phase:** Orchestrates the worker loop, calling connected MCP servers (Web Search, GitHub, Calculator, Document Parser) to gather evidence.
5. **Synthesis Phase:** Compiles data into the final Dual-View report.

---

## 4. Output Deliverables & Plain-English Constraint

No business or technical term may be presented without an immediate, simple analogy (e.g., *CAC = Marketing Cost Per Customer*). 

Every final report features a toggle at the top of the interface:
* **⚡ Quick Insights (2-Min Read):** Conversational language, bullet points, traffic-light status badges, and direct next steps.
* **🔬 Deep Dive (Full Report):** A comprehensive 4-Pillar dossier adapted by motivation (Demand Signals, Defensibility Matrix, 90/10 Architecture, LTV:CAC Unit Economics).

---
---

# System Architecture & Technical Design (v1.2)

## 1. Technology Stack & Security Middleware

| Component | Selected Technology | Architecture Rationale |
| :--- | :--- | :--- |
| **Frontend UI** | Next.js 14, Tailwind | Natively supports SSE for streaming real-time "Agent Thoughts". |
| **API Backend** | FastAPI (Python 3.11+) | Asynchronous execution engine designed for long-running orchestration loops. |
| **Orchestration** | Python `while` loop | Direct provider control over tool execution, state, and bounds without framework bloat. |
| **Tool Layer** | MCP Servers | Decouples tools into isolated servers managed via `mcp-python-sdk`. |
| **Database** | PostgreSQL + `pgvector` (Cloud hosted via Neon/Supabase) | Unified storage for JSON state and dual-namespace vector embeddings. |
| **API Security** | `slowapi` + Redis (Cloud hosted via Upstash) | IP-based rate limiting and global daily spend tracking to prevent abuse of the unauthenticated endpoints. |

## 2. Observability, Cost Control, & Security Guardrails

*   **Untrusted Data Isolation (Anti-Prompt Injection):** All unstructured text returned by external MCP tools (Web Search, GitHub) is treated as adversarial and wrapped in strict `<untrusted_tool_output>` XML bounds before appending to the context window.
*   **Context Pruning:** Raw JSON/HTML output from MCP calls is summarized by a fast model and replaced in the `messages` array, shedding dead token weight before the next tool call.
*   **Tiered Budgets:** 
    *   *Suggester Mode:* $0.15 budget cap | Max 6 steps.
    *   *Evaluator / Optimizer Mode:* $1.25 budget cap | Max 15 steps.
*   **Abuse Prevention (No-Auth Environment):** IP Rate Limiting (Max 3 runs/day per IP) and a Global Kill-Switch (`MAX_GLOBAL_DAILY_SPEND = $10.00`).
*   **Vector Database Architecture (Namespace Isolation):** RAG queries are partitioned into `global_knowledge` (Read-Only) and `session_memory` (Read/Write Isolated by `session_id`).

## 3. Agentic Evaluations (Evals)

Deterministic unit tests are insufficient for verifying LLM output quality. BuildSense implements an automated Eval suite.
* **Framework:** A code-first eval library or custom `pytest`-based LLM-as-a-judge script.
* **Golden Dataset:** A static set of 10 test cases (e.g., "Idea: AI dog walker", "Workflow: Manual Excel invoicing") stored in JSON.
* **Evaluation Criteria:** Every PR or major prompt update must pass an automated grading pass evaluating:
  1. Adherence to the Zero-Jargon rule.
  2. Hallucination rate on market/technical data.
  3. Completeness and actionability of the 4-Pillar CDD report.