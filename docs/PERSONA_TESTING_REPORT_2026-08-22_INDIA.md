# Persona Testing Report — India Scenarios (2026-08-22)

## Scope and method

This session ran a multi-persona, end-to-end QA pass against the live local BuildSense app (backend on `127.0.0.1:8001`, frontend on `localhost:3000`), using the Claude-in-Chrome browser tools to drive the real UI exactly as a user would — no code was read or modified as part of the testing itself. The goal was twofold: (1) re-verify the fix shipped for BUG-050/BUG-046/BUG-047 (evidence-ladder label + sanitizer fact-preservation), and (2) re-probe all previously open bugs (BUG-042, 043, 045, 048, 049, 051) using new India-context SMB personas, replacing the earlier US-based personas that originally surfaced BUG-041–051.

Three personas were planned; two were run fully end-to-end through synthesis, and a third was blocked by the app's own rate limiter before intake could begin (see the Operational Note below — this is the app's guardrail working as intended, not a defect).

| Persona | Business | Location | Outcome |
|---|---|---|---|
| Priya Deshmukh | Deshmukh Textiles & Sarees | Nagpur, Maharashtra | Full run to synthesis |
| Arjun Reddy | Reddy AutoCare Multi-Brand Garage | Hyderabad, Telangana | Full run to synthesis, **two projects** under one company to test cross-project memory |
| Kavita Nair | Nair Homestays & Spice Farm Tours | Wayanad, Kerala | Company created; intake blocked by rate limiter |

All findings below have been logged to `docs/DEFECT_LEDGER.md` in the project's standard format. This document is the narrative companion — what was actually seen on screen, in the persona's own words, and why it matters.

## Headline result: the shipped fix holds, but surfaced something worse

The BUG-050/046/047 fix (generic "Staff / Employee" label instead of hardcoded "Dispatch Manager"; sanitizer no longer hallucinating business categories or dropping stated facts) verified correctly across two independent India personas. Location, staffing counts, family involvement, and an intentionally ambiguous budget statement all survived the sanitizer intact in most turns.

But re-testing the specific "preserve meta-questions" acceptance criterion from BS-3 (BUG-043) surfaced something more serious than the original silent-drop bug. When Arjun asked the assistant, in his own words, *"do you remember anything about my business already, or is this our first conversation?"* — the sanitized input shown back to him, and sent to the model as his own statement, read: *"...This is our first conversation - I have no prior context about your business."* Arjun never said that sentence. The sanitizer invented an answer and put it in his mouth, inside the box labeled "USER INPUT." This is now logged as **BUG-052 (critical)** — fabricating user speech is a step backward from silently dropping it, and it happened intermittently (a later, similar meta-question from the same persona was preserved correctly), which makes it harder to catch.

## The most severe finding: raw internal data leaking into the customer-facing report

Independently reproduced in **both** completed personas' Evidence Ladder Audit Log (Deep Dive tab): instead of showing readable claims, several rows render as raw internal orchestration data — a full base64 extended-thinking signature blob, complete `tool_use` JSON payloads for `market_signal`/`web_search`/`parse_sop_workflow`/`calculate_unit_economics`, and entire `<untrusted_tool_output source="web_search">...</untrusted_tool_output>` wrapper blocks, verbatim. A screenshot from Arjun's session shows this directly in the rendered UI, not just in a text dump — rows of unreadable JSON and cryptographic-looking text sitting in a table meant to build customer trust through transparent sourcing. Logged as **BUG-053 (critical)**. This is the top-priority fix candidate coming out of this session.

## Cross-project memory: definitively confirmed still broken

For BUG-043, this session went further than the original report by creating a **second project under the same company** (Arjun's billing workflow, under Reddy AutoCare) and directly asking the assistant whether it remembered the first project. Its reply: *"I don't have access to your previous project details, so I'd appreciate a quick refresh: where is Reddy AutoCare located?"* — an explicit admission, immediately followed by re-asking a fact already established in project one. This closes the loop on BUG-043 with unambiguous proof text; it remains fully open.

## New findings this session

- **BUG-054 — "Vertical Focus: GENERIC"** shown in the report header for both companies tested, despite each having a specific Industry Vertical set at creation (Wholesale & Distribution; Automotive Repair & Vehicle Servicing).
- **BUG-045, expanded** — the *same* project displayed two different raw, non-matching titles depending on where you look: the project page header read "I'm Arjun Reddy, I run Reddy A...", while that same project's dashboard card read "GENERIC - Mechanic discovers a wor...". Two independent naive-title code paths, neither producing a real summary.
- **BUG-055 — raw markdown rendering as literal text.** `**bold**` and `### Header` syntax shows up unstyled in both Quick Insights and Deep Dive, confirmed visually via screenshot.
- **BUG-056 — mock research tools ignore query content.** `market_signal` and `web_search` returned near-identical, topically irrelevant canned SaaS-billing-tool results for two clearly different auto-garage queries in the same session (one batch even referenced VAT/GST tax software, unrelated to spare-parts sourcing).
- **BUG-057 — SaaS unit-economics applied to a non-SaaS business.** `calculate_unit_economics` was invoked with LTV/CAC/payback-period inputs for a one-time-repair auto garage — a framework that doesn't apply to that business model. To the synthesizer's credit, the nonsensical raw figures were not quoted directly in the final report text (it reasonably reframed everything in plain ₹0-cost terms instead), so this is logged as open but with mitigation noted.
- **BUG-058 — explicit "generate the report now" requests aren't honored immediately.** Both personas had to go through one extra recap-confirmation turn even after directly asking for the report. May be intentional, but there's no faster override, and the "Run Analysis" button doesn't force synthesis either.
- **BUG-059 (minor) — Industry Vertical field inconsistency.** A fixed 4-option dropdown during initial onboarding vs. free-text in the "Create New Company" modal — same field, two different UI contracts.

## What did *not* reproduce as a bug

An earlier working hypothesis mid-session — that all report tabs were completely locked/unresponsive during orchestration — was investigated and ruled out as a false positive caused by reusing a stale element reference in the browser-automation tooling, not a real product defect. It is deliberately **not** included in the defect ledger. Tab switching worked correctly when re-verified with fresh element lookups, even mid-"Evaluating..." state.

## Operational note

The CHANGE-005 rate limiter (max 3 new-session/company creations per day per IP without a BYOK key) correctly blocked further workspace creation after this session's rapid-fire creation of two companies and three projects, preventing Persona 3 (Kavita Nair) from being run to completion. This is the guardrail working as designed, not a defect — but it means a future all-in-one persona sweep should either pace project creation across a longer window or use a BYOK key to avoid running out of headroom mid-session.

## Suggested priority order for fixes

1. **BUG-053** (raw data leak into Evidence Ladder) — customer-facing, looks broken/untrustworthy, reproduced twice.
2. **BUG-052** (sanitizer fabricating user speech) — worse than the bug it replaced; erodes trust in the "USER INPUT" record itself.
3. **BUG-043** (cross-project memory) — now has unambiguous reproduction steps and proof text; was previously somewhat abstract.
4. **BUG-054 / BUG-045** — both are "the report visibly looks unfinished" issues that are cheap, high-visibility fixes.
5. **BUG-055** (markdown rendering) — likely a one-line fix (add a markdown renderer component) with outsized visual impact.
6. BUG-056/057/058/059 — lower severity, worth batching into the next cycle.

Full technical detail, root-cause notes, and files-touched guidance for each item are in `docs/DEFECT_LEDGER.md`, filed in the project's standard ticket format so they're ready to hand to an implementation cycle the same way BS-3 and BS-5 were.

## Addendum: fix re-verification, same day

Later the same day, fixes landed for several of the items above. Rather than assume they worked, this pass read the actual current source of `orchestrator.py` and `main.py` from the app, then re-tested live wherever possible.

**The two most severe findings are confirmed fixed.** BUG-052 (sanitizer fabricating user speech) was re-tested by asking Arjun's existing project a fresh meta-question almost identical to the original repro — the sanitized bubble now preserves it word-for-word, minus the filler word "like." BUG-053 (raw internal data leaking into the Evidence Ladder) was re-tested by feeding a claim containing a trigger keyword ("estimate") into the same project — the Evidence Ladder now shows exactly one clean row with the claim's own text and an "Owner Estimate" label, no JSON, no base64, no tool payloads. Both are the top two items from the original priority list, and both check out.

**Three items have genuine-looking fixes in the code that couldn't be exercised live this pass.** BUG-054 (Vertical Focus: GENERIC), BUG-045 (inconsistent titles), and BUG-043 (cross-project memory) all only run at *new* project creation — and the app's CHANGE-005 rate limiter (max 3 new sessions per IP per day, resetting at UTC midnight) was already exhausted by this session's own earlier testing before these re-checks could run. A canary attempt to finish Persona 3 (Kavita Nair)'s intake confirmed the limiter is still active. The BUG-043 fix in particular is worth flagging: it's a real implementation (pulling prior projects' established facts into a new session's context), but it's unconfirmed whether that assembled context actually gets surfaced to the model or just sits unused in metadata — that's the first thing to check once the limiter allows a live test.

**One bonus, unconfirmed observation:** markdown (`**bold**`, `*italic*`) rendered correctly as styled text in both re-run reports, which the original session logged as broken (BUG-055). This wasn't part of the deliberate re-test list and no header (`###`) syntax was checked, so it's noted as a possible fix rather than confirmed.

Next step is either waiting for the UTC-midnight rate-limit reset (or supplying a BYOK key) to finish the three blocked checks and Kavita's persona, whichever is preferred.
