# Specification: Persona Testing Bug Fixes (BS-6)

## 1. Overview
This specification details the resolution for six bugs identified during the 2026-08-22 India Scenarios Persona Testing session. The primary goal is to address critical UX/security defects, including raw data leakage in the Evidence Ladder and user-speech fabrication in the sanitizer, as well as fixing UI inconsistencies and cross-project memory gaps.

## 2. Scope
The scope includes fixing the following bugs in priority order:

1. **BUG-053 (Critical)**: Prevent raw internal orchestration artifacts (tool calls, thinking signatures, untrusted tool wrappers) from leaking into the customer-facing Evidence Ladder Audit Log.
2. **BUG-052 (Critical)**: Prevent `_node_sanitize_input` from fabricating user speech (e.g., answering meta-questions on behalf of the user).
3. **BUG-043**: Enable cross-project memory by hydrating established company facts into the session context.
4. **BUG-054 & BUG-045**: Fix "Vertical Focus: GENERIC" display in Execution Dossier headers and align project title generation to use summarized semantic labels instead of raw user messages.
5. **BUG-055**: Add markdown rendering support to Quick Insights and Deep Dive report views to correctly parse `**bold**` and `### Header` syntax.

## 3. Acceptance Criteria
1. **Evidence Ladder (BUG-053)**: Only human-readable claim text is rendered in the Evidence Ladder. Tool use JSON, base64 thinking blocks, and `<untrusted_tool_output>` XML are stripped or skipped.
2. **Sanitizer Fidelity (BUG-052)**: Meta-questions are preserved or ignored, but the model never generates first-person user statements that do not appear in the original input.
3. **Cross-Project Memory (BUG-043)**: Subsequent projects under the same company successfully reference facts (e.g., location, business category) established in previous projects.
4. **Header & Title UI (BUG-054/045)**: 
    - The Execution Dossier displays the correct Industry Vertical associated with the company, rather than "GENERIC".
    - Project cards and headers display a consistent, semantically derived project title.
5. **Markdown Rendering (BUG-055)**: All report tabs render standard Markdown elements (bolding, headers, lists) cleanly as HTML.

## 4. Out of Scope
Fixing mock research tools (BUG-056), unit economics SaaS logic (BUG-057), report generation UX overrides (BUG-058), and Industry Vertical onboarding consistency (BUG-059). These will be batched into a future cycle.

## 5. Implementation Approach
- Update `extract_evidence_ledger_from_messages` in `orchestrator.py` to filter out tool use, internal tags, and thinking blocks.
- Strengthen the `_node_sanitize_input` prompt to explicitly forbid first-person speech generation.
- Integrate company context into the orchestrator initialization.
- Fix UI data binding for `company.industry_vertical` and `project.title`.
- Wrap relevant UI report sections in a `ReactMarkdown` component.
