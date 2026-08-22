# Specification: Resolve BUG-050, BUG-046, and BUG-047 (Orchestration & Prompts)

## 1. Overview
This specification addresses three related defects in the orchestration layer:
- **BUG-050:** The Evidence Ladder attributes claims to a hardcoded "Staff / Dispatch Manager" even when inapplicable.
- **BUG-046:** The `sanitize_input` node hallucinated a business category ("Catering business") for a flower shop.
- **BUG-047:** The system exhibits same-session fact amnesia, dropping previously established facts (like location or meta-questions) from the conversation history.

## 2. Requirements & Scope
- **Evidence Ladder (BUG-050):** The hardcoded string "Dispatch Manager" must be removed. The matching logic for Level 2 must not misclassify owner statements as employee statements simply because the word "stated" was used.
- **Fact Preservation & Hallucination (BUG-046 & BUG-047):** The LLM prompt in the `sanitize_input` node must be rewritten to strictly preserve factual details (locations, tools, quantities), conversational context (meta-questions), and must never infer or fabricate business categories. Its sole job is removing conversational filler and adversarial text.

## 3. Out of Scope
- Major architectural changes to the Evidence Ladder beyond fixing the hardcoded actor and keyword misclassification.
- Total removal of the LLM `sanitize_input` node; we will only correct its prompt instructions.

## 4. Acceptance Criteria
- Conversations mentioning "stated" by an owner do not incorrectly get labeled as "Staff / Dispatch Manager".
- The `sanitize_input` node correctly preserves locations, meta-questions, and does not inject hallucinated industry categories.
