# Product Requirements Document: BuildSense

## 1. Executive Summary

BuildSense is an agentic AI intelligence engine for small and midsize businesses. It helps users describe an operational workflow, clarify missing details, analyze evidence, and produce a plain-English modernization plan.

The product is designed around a guided pipeline: **Router -> Planner -> Executor -> Synthesizer**. The pipeline combines structured session state, human-in-the-loop clarification, deterministic tools, and optional LLM synthesis to turn messy process descriptions into actionable recommendations.

## 2. Product Modes

BuildSense is intended to support three modes:

1. **Idea Suggester:** Generates validated business or product concepts tailored to a market, workflow, or technology constraint.
2. **Idea Evaluator:** Audits a raw concept across market demand, defensibility, execution complexity, and economics.
3. **Workflow Optimizer:** Deconstructs a manual business process and recommends practical automation or process improvements.

Current implementation note: the active schema currently exposes `OPTIMIZER`. The broader mode model remains a product target.

## 3. Motivation Adaptation

At intake, the product should adapt recommendations to the user's objective:

1. **Revenue & Growth:** Focus on commercial opportunity, market gaps, unit economics, and monetization.
2. **Education & Learning:** Focus on skill-building, project uniqueness, portfolio value, and low-cost implementation paths.
3. **Operational Efficiency:** Focus on time savings, fewer errors, better handoffs, and repeatable workflows.

## 4. User Experience Flow

1. **Onboarding:** The user creates or selects a company profile with industry and core tools.
2. **Intake:** The user describes a workflow or idea using text, uploaded file content, or audio transcription.
3. **Routing:** The backend classifies the request, validates completeness, and decides whether clarification is required.
4. **Human-in-the-Loop Clarification:** If critical fields are missing, the app pauses and asks plain-English questions before running heavier analysis.
5. **Planning:** The system builds a step-by-step execution plan.
6. **Execution:** Tool calls gather market, workflow, document, calculator, or geographic context.
7. **Synthesis:** The system creates the final report and stores project state, messages, and graph data.
8. **Workspace Review:** The user reviews report, graph, progress, and chat views inside the project workspace.

## 5. Output Requirements

Final outputs must be direct, practical, and plain English.

Every report should support two reading modes:

1. **Quick Insights:** A short, scannable summary with direct next steps and traffic-light style status cues.
2. **Deep Dive:** A fuller dossier covering evidence, workflow diagnosis, implementation path, risks, and expected business impact.

No business or technical term should appear without a quick explanation. For example: `CAC` should be explained as the cost to win one customer.

## 6. Technical Architecture

| Component | Current Technology | Notes |
| --- | --- | --- |
| Frontend | Next.js 14, TypeScript, Tailwind CSS | App Router UI with authenticated company and project flows. |
| Backend | FastAPI, Pydantic v2 | Async API routes for companies, projects, sessions, transcription, and orchestration. |
| Orchestration | LangGraph `StateGraph` | Current implementation uses LangGraph. Repository operating guidance prefers a native Python loop as the long-term direction. |
| Tool Layer | Local MCP-style functions | Web search simulation, market signal lookup, calculator, document parser, and geographic enrichment. |
| Database | PostgreSQL with optional `pgvector` | Stores users, companies, projects, messages, graph data, vectors, and serialized session state. |
| Cache/Budgeting | Redis with local fallback | Used for global spend tracking and rate-limit storage where available. |
| Auth | Supabase-style JWT plus local mock token | Tenant checks are enforced for company and project access. |

## 7. Security And Guardrails

- **Prompt injection isolation:** Untrusted external tool output must be wrapped in `<untrusted_tool_output>` XML tags before entering conversation history.
- **Context pruning:** Large raw HTML or JSON payloads should be summarized and dropped after the relevant step completes.
- **Budget controls:** Sessions must enforce per-mode cost and step caps.
- **Rate limiting:** Public orchestration routes should remain protected by IP-based rate limits.
- **Tenant isolation:** Company, project, session, and `session_memory` reads must be scoped to the authenticated user or current session.
- **Global kill switch:** New runs should be rejected once the configured daily spend cap is reached.

## 8. Evaluation Requirements

BuildSense uses deterministic tests and LLM-as-a-judge evaluations.

Required checks for significant orchestrator or prompt changes:

1. Unit and integration tests under `apps/api/tests`.
2. Agentic evals under `apps/api/evals`.
3. Zero-jargon scoring.
4. Hallucination and evidence-quality scoring.
5. Completeness and actionability scoring for final reports.

## 9. Current Product Gaps

- The docs describe three product modes, while the current schema only enables `OPTIMIZER`.
- The documented target architecture says native Python orchestration, while the current backend uses LangGraph.
- Some frontend files still use broad `any` types.
- Some visible UI strings contain encoding artifacts and should be normalized.
- Local database and Redis fallback behavior is useful for development but should be surfaced clearly during integration testing.
