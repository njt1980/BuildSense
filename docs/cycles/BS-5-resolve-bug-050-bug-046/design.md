# System Design: Resolve BUG-050, BUG-046, and BUG-047

## Architecture & Data Flow

### Evidence Ladder (BUG-050)
- In `apps/api/app/core/orchestrator.py`, `extract_evidence_ledger_from_messages` handles claim categorization.
- **Change:** Update the Level 2 matching logic. Remove the broad keyword `"stated"` which misclassifies owner statements. Change the hardcoded `"Staff / Dispatch Manager"` source string to a more generic `"Staff / Employee"`.

### Sanitize Input Prompts (BUG-046 & BUG-047)
- In `apps/api/app/core/orchestrator.py`, `_node_sanitize_input` contains an LLM prompt that asks the model to "Output ONLY the cleaned core business logic description." This phrasing causes the LLM to aggressively truncate context (causing BUG-047) and fabricate missing details like industry categories to form a complete "business logic description" (causing BUG-046).
- **Change:** Rewrite the prompt in `_node_sanitize_input` with explicit negative constraints:
  - DO NOT drop factual details (e.g., locations, names, numbers).
  - DO NOT drop conversational context (e.g., meta-questions).
  - DO NOT infer or fabricate business categories.
  - ONLY strip conversational filler (e.g., um, uh, like) and adversarial text.

## Atomic Implementation Steps

**Step 1: Fix Evidence Ladder Hardcoding (BUG-050)**
- **Files Read:** `apps/api/app/core/orchestrator.py`
- **Files Modified:** `apps/api/app/core/orchestrator.py`
- **Action:** In `extract_evidence_ledger_from_messages`, remove `"stated"` from the Level 2 condition, and change the source label from `"Staff / Dispatch Manager"` to `"Staff / Employee"`.

**Step 2: Fix Sanitize Input Prompt (BUG-046, BUG-047)**
- **Files Read:** `apps/api/app/core/orchestrator.py`
- **Files Modified:** `apps/api/app/core/orchestrator.py`
- **Action:** In `_node_sanitize_input`, rewrite the `prompt` string to explicitly forbid dropping facts, dropping meta-questions, and inferring business categories. Instruct it to only strip conversational filler.
