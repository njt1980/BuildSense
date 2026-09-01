# Rate Limiting Enhancement Specification (BS-RATE-LIMIT)

## Problem Statement
The current rate-limiting implementation on the `/api/v1/orchestrate` endpoint enforces a strict limit of `5/day` using `slowapi`. Because this endpoint handles both new session creation and in-session conversational turns (e.g., answering clarification questions), the current architecture restricts users to merely 5 individual chat messages per day. This severely hinders the "Progressive Discovery" workflow, where users are expected to have an extended back-and-forth conversation. Additionally, users supplying their own API keys (BYOK) are still penalized by budget-focused constraints.

## Goal
Revise the rate-limiting architecture to limit the creation of *new sessions* per day while allowing a reasonable number of intra-session interactions, and appropriately exempt BYOK users from restrictive cost-based limits.

## Scope of Changes
1. **Targeting New Sessions**: Apply the strict daily rate limit (`3/day`) to new project/session creation, rather than individual orchestration turns, to align with the intent of `AGENTS.MD`'s "Max 3 full runs per IP per 24 hours".
2. **Intra-Session Limits**: Allow orchestrator resume requests (where `session_id` is present) to bypass the strict daily IP limit, instead relying on existing cost controls (`max_budget_usd`, `max_steps`).
3. **BYOK Exemption**: Update the rate limit application to exempt requests containing a valid `x-user-anthropic-key` from the standard 3/day IP limit, as these requests do not impact the system's global spend budget.
4. **Documentation Sync**: Update `AGENTS.MD` and `docs/DEFECT_LEDGER.md` to clarify that the "Max 3 full runs" rule applies strictly to new session instantiations.

## Acceptance Criteria
- [ ] Users can send more than 5 messages in a single ongoing session without encountering a `429 Too Many Requests` error.
- [ ] Users without a BYOK key are restricted to creating a maximum of 3 new sessions/projects per IP per 24 hours.
- [ ] Users with a BYOK key (`x-user-anthropic-key` present) can create more than 3 sessions/projects without hitting the `429` error.
- [ ] The codebase documentation (`AGENTS.MD`, `docs/DEFECT_LEDGER.md`) explicitly details this refined abuse-protection logic.
