# Persona Testing Report — Kochi Kirana Scenario (2026-08-24)

## Scope and method

This session ran an autonomous, end-to-end persona diagnostic against the **real BuildSense backend** — not a scripted simulation of both sides. The FastAPI app (`apps/api`) was copied into an isolated environment, its dependencies installed fresh from `requirements.txt`, and driven directly over its actual `/api/v1/orchestrate` HTTP contract (no UI, so this pass does not cover React/rendering bugs — see the existing `PERSONA_TESTING_REPORT_2026-08-22_INDIA.md` for that class of finding). Every quoted assistant line below is genuine model output from the live orchestrator, using the project's own `ANTHROPIC_API_KEY`.

Persona: **Suresh**, who runs **Chandran General Stores**, a family Kirana (grocery) shop in Kochi, Kerala, started by his father. Human stakes and messy tooling were revealed organically over the conversation rather than front-loaded: 6am–10pm days, a nephew (Vinu) who is the shop's only real backup and is actively job-hunting in Bangalore, WhatsApp as the entire order-intake system, a paper *khata* credit ledger his wife runs, and a mid-conversation correction ("wait, actually Vinu checks WhatsApp too").

**Important caveat on method:** the first full attempt at this run surfaced a real, severe infrastructure bug (below) that silently degraded the conversation into generic fallback text. That run is preserved as Finding 1 evidence. A second, clean run — after fixing the dependency issue locally — is the one this report's Phase 1/UX scoring is based on, since it reflects genuinely healthy, LLM-backed operation. Both runs are real BuildSense output; neither is fabricated or hand-written.

---

## Critical infrastructure finding (found before persona scoring could even begin)

### Finding 1 — CRITICAL: Unpinned `anthropic` SDK breaks 3 of 4 intake LLM calls on any fresh install, and fails silently

`apps/api/requirements.txt` does not pin (or even list) the `anthropic` package at all. A fresh `pip install` today pulls the newly-released `anthropic==1.0.0`, which dropped support for the `temperature` keyword argument on `messages.create()`. Three call sites in `app/core/orchestrator.py` still pass `temperature=0.0` (`sanitize_input`, `extract_process_components`, `generate_clarification_question`), so **every single intake turn** threw:

```
TypeError: AsyncMessages.create() got an unexpected keyword argument 'temperature'
```

confirmed by direct reproduction against the installed SDK. This is not a network/auth failure — it happens in ~0.2ms, before any request leaves the process.

**Why this is dangerous rather than just broken:** the failure is invisible. The orchestrator catches the exception and falls through to generic fallback behavior that still *looks* like a working product:
- `process_components` (trigger/actor/activity/system) stayed `"UNKNOWN"` for the entire session despite the persona giving specific, on-topic answers to every question.
- The clarification-question generator fell back to identical canned text — turn 2 and turn 3 both returned the verbatim string *"Got it. What happens next in that workflow?"* regardless of what was actually said.
- `context_architect`'s fallback path misattributed the business's own location as **"Bangalore"** — lifted from an aside about the nephew's aspirational IT job, not anything said about the shop — and called the `geographic_market_mapping` tool against that wrong city. The real location ("Kochi") was never asked for or captured in this run.
- Despite all of that, the final synthesis call (`execute_tools`/report generation, which happens not to pass `temperature`) still succeeded and produced a fluent, well-organized report — meaning **a completely broken intake pipeline can still ship a report that reads as if nothing went wrong.**

**Root cause confirmed by direct repro**, not inference — reinstalling `anthropic==0.125.0` eliminated the `TypeError` immediately, and a from-scratch rerun with the same persona correctly captured Kochi as the location, richly populated `process_components`, and never repeated a canned question.

**Recommendation:** pin `anthropic` in `requirements.txt` to a tested range, and add a one-line startup/CI smoke test that makes a real `messages.create()` call so a future breaking SDK release fails the build instead of silently degrading every conversation.

### Finding 2 — Operational: transient `401 invalid x-api-key` mid-session

The key in `.env` returned a real `AuthenticationError` from Anthropic directly (confirmed independent of the SDK-version bug above, and at zero token cost since auth failures aren't billed) partway through this session, then worked again on retry a few minutes later without any change on this end. Flagging for awareness — a live key oscillating between valid and invalid is worth a look on the account/dashboard side, since it could intermittently take down the whole app in production the same way Finding 1 did.

---

## Phase 1 transcript (clean run, genuinely LLM-backed throughout)

> Session `0b09a233-984e-40bf-84e4-ee3987c6f0b4`. Zero LLM-call failures this run (verified via the local telemetry log); `geographic_market_mapping` was correctly called with `"Kochi, near the market area"` every time.

**Suresh:** I run a small grocery shop and I keep losing track of orders and stock. Can you help me figure out what's going wrong? I don't have much time to explain everything so let's make this quick.

**BuildSense:** Perfect—I hear you, and I respect that you're busy. Losing track of orders and stock is a real problem that eats into your day and your margins, so let's dig into this smartly. Here's what I want to do: I'll ask you a few quick, concrete questions... Where is your grocery shop located?

**Suresh:** we are in Kochi, near the market area. small shop, been running it since my father started it

**BuildSense:** Got it—a family shop near the market, that's a solid foundation... So when you need to order stock, what usually kicks that off—is it when a supplier calls you, when you notice shelves running low, or something else?

**Suresh:** when I notice shelves getting low, or if a regular customer asks for something we don't have. I open the shop around 6:30am and first thing I do is check WhatsApp because customers send their order list at night for morning delivery - rice, oil, milk packets, that sort of thing

**BuildSense:** Perfect! So here's what I'm hearing—let me make sure I've got this right: [playback summary]... Does that capture it? Anything I'm missing or got wrong?

**Suresh:** that's mostly right, but also - my nephew Vinu checks it too sometimes when I'm busy with deliveries. the bigger problem is deliveries - we send the wrong item or forget someone and they call angry

**BuildSense:** Ah, thanks for that—that's really important. Let me update what I'm hearing: [updated playback]... Is that the real problem we need to solve?

**Suresh:** That's exactly it. What worries me more is Vinu keeps talking about doing a computer course and getting an IT job in Bangalore. If he leaves I don't know who helps me with deliveries and WhatsApp. I am already working 6am to 10pm most days.

**BuildSense:** I hear you—that's the real worry underneath all of this. You're already stretched thin from 6am to 10pm, and Vinu is your lifeline right now for deliveries and keeping up with WhatsApp. If he leaves, you're looking at doing all of this alone, which just isn't sustainable. Here's what I need to understand: when a customer order comes in on WhatsApp and you're out on a delivery, how does Vinu know which items to pick and pack for that customer right now?

**Suresh:** he reads the WhatsApp messages on my phone directly, there is no separate list. my wife handles the counter and the paper khata ledger for regular customers who buy on credit, but she gets annoyed when I let people run up big credit without checking

**BuildSense:** I have completed my analysis. Your Executive Report is ready. Please view the Quick Insights and Deep Dive tabs for the full breakdown.

*(Full report text — As-Is Workflow, ROI Economics, Friction Analysis, Tiered Recommendations — captured in full in the session logs; key excerpts quoted in the findings below.)*

---

## Additional findings from the clean run

### Finding 3 — MEDIUM: Evidence Ledger populates on an 8-word keyword whitelist, not real claim extraction

`extract_evidence_ledger_from_messages()` only logs a claim if the message literally contains one of: `export`, `database`, `system`, `manager`, `staff`, `employee`, `estimate`, `assume`, `think`. Across two full sessions and 12+ substantive user messages (angry customers, wrong deliveries, credit disputes, 16-hour days), the Evidence Ledger stayed **completely empty**, because none of those exact words happened to appear. The final report's own "Unverified Assumptions" callouts are good and compensate for this in the text the user sees — but the structured Evidence Ladder feature that the Deep Dive tab is built around has very poor recall by design, independent of the SDK bug above.

### Finding 4 — MEDIUM: Synthesis invented a specific, unverifiable named citation

Both the degraded run and the clean run independently generated: *"per general small-business operations research (such as patterns cited in the Gartner Small Business Operations Index...)"*. A web search turned up no such Gartner publication — the closest real Gartner titles are things like *"Forecast: Small and Midsize Business IT Spending"*. No `web_search`/`market_signal` tool call backed this citation in telemetry either time. This is a fabricated-sounding, specific proper noun invented to lend authority to a benchmark estimate — worse than saying "general industry patterns suggest," which is what the model does everywhere else in the same report. It appearing independently twice suggests a systematic pattern rather than a one-off.

### Finding 5 — LOW: `playback_shown` / `playback_confirmed` flags never flip to `True`

Even in the clean run, where a genuine playback-and-confirmation exchange visibly happened twice in the transcript, `SessionState.playback_shown` and `.playback_confirmed` stayed `False` in every snapshot. Not user-visible, but likely dead or inconsistent bookkeeping worth reconciling, since other logic may depend on it.

### Finding 6 — LOW: Sanitizer rewrites voice, not just filler

The sanitizer is scoped to "ONLY strip conversational filler... DO NOT drop factual details," but in practice it also corrects grammar/capitalization and smooths phrasing (e.g. "we are in Kochi, near the market area" stayed close to verbatim, but the opening message's run-on lowercase typing was reflowed into polished, capitalized prose before being echoed back as "the user's own message"). Facts were preserved faithfully both times — this is a voice/authenticity note, not a data-integrity one.

---

## Meta-Judge Evaluation (Phase 2)

```json
{
  "overall_verdict": "FAILED",
  "composite_scores": {
    "personal_conversational_ux": 0.93,
    "diagnostic_rigor_viability": 0.82,
    "final_delivery_quality": 0.85
  },
  "detailed_scores": {
    "consultative_empathy_score": 0.88,
    "cognitive_pacing_score": 0.90,
    "zero_jargon_score": 0.92,
    "fourth_wall_integrity_score": 1.00,
    "correction_grace_score": 0.95,
    "workflow_atom_coverage_score": 0.85,
    "exception_and_edge_case_score": 0.88,
    "constraint_and_practicality_score": 0.82,
    "solution_hierarchy_score": 0.95,
    "epistemic_rigor_score": 0.60
  },
  "persona_experience_summary": "Once genuinely LLM-backed, BuildSense handled Suresh's story with real warmth and specificity — it named his exact stakes back to him (6am-10pm, Vinu as his 'lifeline'), absorbed a mid-conversation correction gracefully, paced one plain-English question at a time, and never broke the fourth wall. The final report's Tier 1/2/3 discipline and refusal to over-engineer a GenAI fix for a low-volume shop was genuinely excellent and India-appropriate (named ₹300-500/month regional tools). The two real misses were epistemic: a fabricated-sounding named research citation with no grounding, and an Evidence Ladder that structurally can't populate from a normal conversation. Separately, this test surfaced a critical, easy-to-miss production risk: a routine dependency install today silently breaks most of the intake pipeline while the app still visibly 'works'.",
  "strengths": [
    "Specific, non-generic empathy directly referencing the persona's stated time poverty and staff-loss fear, not templated sympathy.",
    "Strict, well-reasoned Tier 1 -> Tier 2 -> Tier 3 recommendation discipline, with an explicit, sound argument for NOT building a GenAI solution given the shop's order volume.",
    "Recommended realistically-priced, regionally-appropriate named tools (Vyapar/Khatabook, ~Rs.300-500/month) rather than generic Western SaaS.",
    "Smoothly absorbed a mid-conversation correction ('actually Vinu checks it too') without arguing or repeating stale framing.",
    "Caught a genuinely non-obvious blind spot (an ungoverned credit-approval process) from one passing remark at the very end of intake.",
    "Zero fourth-wall leakage (no turn_index/confidence_score/Trigger/Actor/Friction/Market Pillar) in any user-facing text across two full runs.",
    "Consistent, natural inline glossing of every technical term with a plain analogy."
  ],
  "friction_points_and_regressions": [
    "CRITICAL: requirements.txt does not pin `anthropic`; today's latest release (1.0.0) breaks the `temperature` kwarg used by 3 of 4 intake LLM calls, causing silent TypeErrors on every turn that fall back to generic/templated behavior indistinguishable from normal operation to a casual observer.",
    "That degraded fallback state produced a real, reproducible hallucination: the business's own location was mis-set to 'Bangalore' (the nephew's aspirational job city) and a geo-enrichment tool was called against the wrong city.",
    "Evidence Ledger extraction uses an 8-word keyword whitelist and stayed empty across two full, fact-rich sessions -- the Deep Dive audit trail this feature is meant to power has very poor real-world recall.",
    "Synthesis fabricated a specific, unverifiable named research citation ('Gartner Small Business Operations Index') with no backing tool call, in both runs independently -- a systematic pattern, not a fluke.",
    "playback_shown/playback_confirmed state flags never became True even during a real, visible playback-and-confirmation exchange.",
    "The sanitizer smooths grammar/voice beyond stripping filler, and that rewritten text is echoed back as the owner's own words -- facts stayed intact both times tested, but the owner's authentic voice did not.",
    "The ANTHROPIC_API_KEY returned a transient 401 mid-session before working again on retry, unrelated to anything on this end.",
    "No question was ever asked about budget or comfort with technology before the report recommended a paid Rs.300-500/month tool; 'financials' stayed flagged as a missing pillar the entire session."
  ],
  "concrete_prompt_patches": [
    "Pin `anthropic` to a tested version range in requirements.txt, and add a startup/CI smoke test that makes one real messages.create() call so a breaking SDK release fails the build loudly instead of degrading every conversation silently.",
    "Make sanitize_input / extract_process_components / generate_clarification_question failures surface loudly (session FAILED status, alert, or at minimum a distinct log level) rather than falling back to fallback text that looks identical to healthy operation.",
    "Replace or supplement the 8-keyword Evidence Ledger whitelist with an LLM-based claim classifier so it reflects what users actually say.",
    "Add an explicit synthesis-prompt instruction: 'Never name or imply a specific research report, index, or study unless it was retrieved via a tool call this session; use only generic phrasing like general small-business benchmarks suggest.'",
    "Ask one direct budget/tech-comfort question before recommending any paid Tier 2 tool, especially when the financials pillar is still flagged missing.",
    "Reconcile playback_shown/playback_confirmed bookkeeping with the actual conversation flow."
  ]
}
```
