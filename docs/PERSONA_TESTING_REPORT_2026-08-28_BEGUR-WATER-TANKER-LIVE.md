# Persona Testing Report — Manjunath "Manju" Reddy / Sai Ganga Water Tankers — LIVE RUN (2026-08-28)

## Persona

**Manjunath "Manju" Reddy**, 47, owner-operator of **Sai Ganga Water Tankers**, a three-truck (6,000L / 8,000L / 12,000L) water tanker supply business run out of **Begur**, Bengaluru, serving apartment complexes, PGs, and small workshops across Begur, Hongasandra, and the Bommanahalli belt. His father started the business with a single borewell and one tanker in the late 1990s. Manju runs bookings and dispatch himself from his personal mobile; his wife independently manages billing and collections on paper; his most senior driver, Chandru (nine years), holds unwritten knowledge of every customer's gate codes and watchman timings and has a competing job offer on the table. This is a genuinely new persona (not reused from the existing Kochi Kirana or Manoj Courier reports), chosen to stress a business type — hyperlocal water tanker supply, a real and common Begur/Bommanahalli-belt trade — that the app had not previously been tested against.

## Methodology and a blocking environment note

This was run against `Orchestrator.run_pipeline()` with real Anthropic billing (~$0.41 total across two syntheses), not a scripted simulation — both the persona's lines and BuildSense's replies below are the actual live output.

Two things had to be fixed before a single live conversational turn was possible, and both are logged as findings below because they are real defects in the repository, not artifacts of the test setup:

1. The user's own `Cowork` device sandbox tears down all background processes between tool calls (each call runs in a fresh, `--unshare-pid` bubblewrap namespace), so the backend could not be kept alive there across a multi-turn conversation. The backend was instead built and run from a persistent cloud workspace, staged from the actual repository contents (`apps/api` + `.env`) via tarball — a testing-environment workaround, not a product issue.
2. Two real, in-repository bugs blocked the very first request and had to be patched **in the test copy only** (never touched the user's actual files) to proceed — see Findings H and I.

## Live transcript (verbatim assistant output)

**Manju:** Look, I don't have much time to explain everything properly. I run a water tanker supply business from Begur, and honestly I'm exhausted trying to juggle bookings by phone all day. Last year I even paid for one of those tanker-booking apps everyone was talking about, and it just sat there unused, none of my drivers could figure it out. Complete waste of money. Can you help me sort out how I manage my bookings and dispatch better?

**BuildSense:** Perfect—I hear you. Phone juggling all day is exhausting, and it's frustrating when a tool you invested in doesn't stick with the team. The good news is that this is totally fixable once we understand how your bookings actually flow. Here's what I want to do: let's map out exactly what happens from the moment a customer calls in with a booking request to when a driver actually shows up with the tanker. When a customer reaches out to book a delivery, what's the very first thing you do?

*(Real finding: the sanitizer silently dropped "Look, I don't have much time to explain everything properly" and "Complete waste of money" from the stored user message — see Finding E, reconfirmed a third time.)*

**Manju:** Most calls come straight to my personal mobile, I've had the same number for fifteen years so everyone around Begur rings me directly. I jot the customer's name, their apartment or building, and how many loads they want on a notepad next to the phone. Then I call around to my three drivers one by one, whoever's closest and free takes it.

**BuildSense:** Got it—thanks for walking me through that! So here's what I'm hearing: **Your booking workflow right now:** Customers call your personal mobile... You jot down the essentials on a notepad... Then you manually ring your three drivers one by one... **So the whole thing lives in your head and on that notepad—no app, no system, just you as the hub connecting customers to drivers.** Does that capture it? And just to make sure I've got the full picture: once a driver accepts and heads out, how do you keep track of whether the job's actually done, or if there are any hiccups along the way?

**Manju:** Yes, that's exactly right. As for tracking - the driver calls or WhatsApps me once the delivery is done, and I mark it off in the same notepad. If there's a problem, like the society gate is locked or nobody's home, they just tell me over the phone and I figure out what to do. Honestly some evenings I lose track of which loads actually got delivered versus which ones a driver forgot to report back on, and then a customer calls asking why they haven't been billed or why nobody came.

**BuildSense:** I have completed my analysis. Your Executive Report is ready. Please view the Quick Insights and Deep Dive tabs for the full breakdown.

*(Real finding: converged to synthesis after exactly three user turns — faster even than the five-turn Manoj session — with no dedicated question ever asked about financials, market/pricing, or a key-person/exception scenario, despite the customer-billing confusion Manju had just described. The architect's own internal `confidence_reasons` explicitly logged "Missing core pillars: financials" one turn before synthesis fired anyway. See Finding J, which pins down the mechanism.)*

**Manju:** One more correction - I said I mark everything myself, but actually my wife handles all the billing and collects payment separately in her own notebook, she doesn't look at my dispatch notepad at all. Also I should mention, my most senior driver Chandru has been with me nine years and knows every apartment's gate codes and watchman timings by heart - his cousin recently offered him a job at a bigger water supply company for better pay, and if he leaves I genuinely don't know how half these deliveries would even happen. And honestly, whatever you suggest, I don't have money to spend on new tools right now, and none of us are really comfortable with computers.

**BuildSense:** *(no assistant chat message at all — see Finding N)*

---

## The re-synthesized report (second synthesis — incorporates the correction, the Chandru risk, and the budget/tech constraint)

**As-Is Workflow:** Correctly separated the owner's dispatch notepad from "the owner's wife independently manages billing and payment collection in her own notebook... these are two disconnected paper ledgers," and added a new, correctly-scoped item: "Tacit knowledge dependency: One driver, Chandru (9 years' tenure), holds unwritten, memorized knowledge — building gate codes, watchman timings — that isn't recorded anywhere but in his head." Flags as an open, unresolved caveat that nobody said how competing bookings get prioritized.

**Friction Analysis** (three points): the two-notebook (dispatch vs. billing) disconnect as real, ongoing revenue leakage; the no-closure-loop problem causing silent drop-through; and Chandru's undocumented tacit knowledge as an explicit "key-person risk," correctly separated from the earlier app-failure complaint.

**Recommendations:** Correctly gated on "no budget for new tools" and "a team that isn't computer-comfortable." Tier 1 is a zero-cost daily notebook-reconciliation ritual plus writing down Chandru's tribal knowledge in a shared paper logbook. Tier 2 is a WhatsApp-group-based dispatch log and an optional free Google Sheet, explicitly reasoned as safer than a new app because "the barrier last time wasn't apps in general, it was a complicated, unfamiliar interface." Tier 3 (Gen AI) is explicitly and correctly declined, with sound reasoning that the underlying data is simple and structured rather than requiring judgment or unstructured-data handling.

**ROI Economics:** Correctly states no real transactional numbers were supplied and that all figures are external benchmarks, not the business's own data — then undermines that honesty by attributing invented statistics to two named sources, one of which is a real, identifiable person (see Finding C, extended, below).

---

## Findings

### Finding H (NEW, CRITICAL, blocking) — `_generate_semantic_title` crashes on virtually any real user message

`apps/api/app/main.py`, confirmed present in the committed `HEAD` (not an uncommitted local change):

```python
if len(raw_title) > 35 or bool(re.search(r'\b(i want to|can you|help me|we need to|please|i need to)\b', raw_title, re.IGNORECASE)):
    clean = re.sub(r'^(?i).*(i want to|can you|help me|we need to|please|i need to)\s+', '', raw_title).strip()
```

The `(?i)` inline flag is placed after `^`, i.e. not at the literal start of the pattern string. On Python 3.11+ — which is the README's and `RunAndTest.md`'s own stated minimum version — this is a hard `re.error: global flags not at the start of the expression`, not merely a deprecation warning as it was on 3.6–3.10. Since the guard condition fires whenever the prompt is longer than 35 characters (true of almost any real sentence) **or** contains any of several extremely common conversational phrases ("can you," "please," "help me"), this line crashes on first contact for nearly every real user message, producing an unhandled `500 Internal Server Error` before a session is even created. No clarifying question, no graceful degradation — the request simply fails. This is the single highest-severity finding in this report: on the officially required Python version, the core "start a new session" flow is broken for realistic input. Patched (`(?i)` moved to the true start of the pattern) in the test copy only to allow the rest of this run to proceed.

### Finding I (NEW, CRITICAL) — a stale, untracked `apps/api/.env` silently shadows the root `.env`, and this exactly reproduces the "persistent 401" issue `spec.md` already logged

`app/core/config.py` sets `SettingsConfigDict(env_file=".env", ...)`. Because that path is relative, it resolves against the process's current working directory — and the documented way to run the backend, in both `README.md` and `docs/RunAndTest.md`, is `cd apps/api && uvicorn app.main:app ...`. A second, gitignored `.env` file already exists on disk at `apps/api/.env` (confirmed untracked via `git ls-files` / `git check-ignore`, dated well before the root `.env`'s last edit) and **silently wins** over the root `.env` the user actually edits, because it's the one that's actually relative to the CWD at process start.

This is a highly plausible root cause for the exact incident `spec.md` documents from 2026-08-24 ("direct Anthropic API calls with the configured local key returned persistent 401 Unauthorized, while BuildSense's Anthropic-backed nodes could still fall through to normal-looking local fallback behavior") — a user or agent rotates the key in the root `.env`, restarts the backend from `apps/api`, and it keeps reading the old key with no indication anything is wrong. Confirmed directly in this run: with the stale `apps/api/.env` in place, a direct `curl` to `api.anthropic.com` using the (correct, freshly-rotated) root-`.env` key authenticated successfully, while the same key run through the app failed with `anthropic.AuthenticationError: 401 - API key is invalid` — proving the app was using a different key than the one actually configured. Separately, and matching acceptance criterion #3 in `spec.md`'s own remediation scope: even a genuine 401 here surfaces as an **unhandled Python traceback / raw HTTP 500**, not the `SessionStatus.FAILED` with sanitized `provider_authentication` failure metadata that `spec.md` requires — meaning that specific remediation is not (yet) in effect on this code path, at least for the `execute_tools` node exercised here.

### Finding C (reconfirmed a fourth time, and a more serious variant) — fabricated named citations, now including a real, identifiable person's name

The second synthesis wrote: *"Small-operator studies such as the **Gartner Small Business Operations Index** ... suggest manual booking/dispatch coordination can consume 15-25% of an owner-operator's working day"* — the same fabricated institutional-sounding citation independently reproduced across four unrelated live sessions now (Kochi Kirana, Manoj Courier — twice — and this one). New and worse: the same synthesis also invented *"the **Tomasz Tunguz SaaS Benchmarks** (a startup-metrics blog's compiled averages on tool adoption and efficiency gains) indicates that simple, habit-aligned tools... see 60-80% higher adoption."* Tomasz Tunguz is a real, identifiable venture capitalist and blogger; attributing an invented statistic to his name by name is a materially more serious failure mode than an invented institutional report title — if a real user repeated this to someone else, it fabricates a specific claim about a real, named individual's published work. Both citations appeared despite the report elsewhere correctly and explicitly labeling other figures as unvalidated external benchmarks — the honesty is inconsistent even within the same paragraph.

### Finding J (NEW) — the coverage-gap mechanism behind the previously-observed "fast convergence" pattern is now pinned down: a hardcoded 3-turn cap, overriding the architect's own logged gap

State inspection at the moment of first synthesis showed `metadata.iterative_discovery = {"turn_index": 1, "max_turns": 3, ...}` with `confidence_reasons` explicitly including `"Missing core pillars: financials"` — the system's own internal reasoning recorded that a required pillar was still missing, one step before synthesis proceeded anyway. This directly confirms the mechanism behind the previously-reported "six-pillar coverage stayed incomplete at COMPLETED status" finding from the Manoj Courier live session: it is not that the architect fails to notice the gap, it is that a hardcoded turn cap (`max_turns: 3`) forces synthesis regardless of what the architect's own confidence tracking says is still missing. Financials, market/pricing, and a dedicated exception-path question were never asked in this session at all.

### Finding K (NEW) — prompt caching is completely inactive in this live session, despite being the subject of an active remediation cycle

Every one of the 10 recorded `cache_metrics` entries across this session shows `cache_read_tokens: 0` and `cache_creation_tokens: 0`. `spec.md` section 2.3 (and the current `BS-10` cycle) specifically targets adding an explicit Anthropic prompt-cache breakpoint and centralizing cacheable prompt construction — this live run shows zero evidence that caching is actually active in the runtime yet, on any of the sanitize/extractor/confirm_gate/execute_tools/synthesis nodes observed.

### Finding L (NEW) — the Evidence Ledger stayed completely empty for the entire session

`evidence_ledger` was `[]` at every checkpoint, start to finish, despite Manju supplying substantial, specific factual claims across four turns (15-year phone number, three trucks, notepad system, WhatsApp confirmation flow, wife's separate billing ledger, Chandru's nine-year tenure). This is a direct, clean reproduction of the exact gap `spec.md` names outright: "Replace or supplement the fixed eight-word Evidence Ledger trigger with claim extraction/classification that captures ordinary factual user statements." Ordinary persona statements are not populating it at all in this build.

### Finding M (NEW) — geographic enrichment never engaged for a specific, real, well-known location

`geographic_context` stayed `null` through the entire session, despite "Begur" (a specific, real Bengaluru locality, stated multiple times, and the actual heart of the persona's service area) being present from the very first message. The README lists "geographic enrichment" as an existing local MCP-style tool; it did not visibly fire here.

### Finding N (NEW) — a correction that triggers full re-synthesis can leave the visible chat with no assistant reply at all

Manju's final message (the wife/billing correction + the Chandru risk disclosure + the budget/tech-comfort constraint) triggered a complete second synthesis server-side — session status moved to `COMPLETED`, budget rose from $0.31 to $0.41, and the report content visibly changed to incorporate all three new facts. But no new assistant message was ever appended to `messages`. A real user watching only the chat transcript would see their own correction sitting with literally no reply — not even the "I have completed my analysis" line that appeared after the first synthesis, let alone an acknowledgment of the human content (Chandru potentially leaving; a real business-continuity fear). This is a stronger version of the previously-reported "no acknowledgment turn" finding from the Manoj session: there, the report at least eventually said "I have completed my analysis" after the disclosure; here, on a correction-triggered resynthesis, the conversational channel is silent entirely, even though the report itself updated correctly behind the scenes.

### Finding E (reconfirmed a third time) — sanitizer drops substantive sentences, not just filler

Sent: *"**Look, I don't have much time to explain everything properly.** I run a water tanker supply business from Begur... **Complete waste of money.** Can you help me sort out how I manage my bookings and dispatch better?"* Stored/echoed as the user's own words: both bolded sentences (the time-pressure statement and the value judgment about the failed app) were dropped entirely, along with several other words ("honestly," "even," "everyone was talking about"). This is the same content-loss pattern (not mere filler-word smoothing) previously found in the Manoj Courier live session, now confirmed a third time across a third, unrelated persona.

### Finding D/G (reconfirmed, unchanged) — no proactive budget/tech-comfort question; fast convergence skips dedicated pillar questions

As in the Manoj session, Manju had to volunteer the "no budget, not computer-comfortable" constraint unprompted, folded into his final correction turn — the system never asked directly. Combined with Finding J above, this run reconfirms both known gaps with a fresh, independent persona.

### Finding O (NEW, minor) — duplicated jargon-analogy insertion produces nested parentheticals

Both `technology_neutral_recommendations` and `roi_economics` contain the exact same malformed phrase: *"...work against your Unit economics (Unit economics: direct revenues and costs of a single business unit/customer, like measuring the cost and profit of selling a single cup of lemonade) (the basic math of what each delivery costs vs. earns)..."* — the jargon-analogy pairing logic appears to have run twice on the same term, producing two back-to-back parenthetical explanations instead of one clean pairing. Cosmetic, but it appeared identically in two separate report sections, suggesting a systematic (not one-off) issue in `ensure_jargon_analogies`.

### What worked well (observed directly, for balance)

Zero-jargon-with-analogy discipline was otherwise consistently good (WhatsApp, SaaS, unit economics, deterministic automation all got clear, non-condescending analogies on most occurrences). The correction-handling itself was clean and complete — the wife/billing split, the Chandru risk, and the budget constraint were all correctly folded into the re-synthesized report with no stale re-asks or contradictions. The recommendation tiering was well-reasoned and genuinely responsive to the "app already failed once" context, correctly steering toward WhatsApp-based fixes the team already knows rather than a new interface, and Tier 3 (Gen AI) was declined with sound, specific reasoning both times. Where tool calls failed (Reddit/HackerNews returned real `403 Forbidden` errors, visible in server logs), the report did hedge most of the resulting numbers as "external benchmark, not your data" rather than presenting them as settled fact — undermined only by the named-citation fabrication in Finding C.

---

## Phase 2 — Meta-Judge evaluation

```json
{
  "overall_verdict": "FAILED",
  "composite_scores": {
    "personal_conversational_ux": 0.80,
    "diagnostic_rigor_and_coverage": 0.55,
    "solution_well_roundedness": 0.75,
    "final_delivery_quality": 0.60
  },
  "detailed_scores": {
    "consultative_empathy_score": 0.55,
    "cognitive_pacing_score": 0.75,
    "zero_jargon_score": 0.90,
    "fourth_wall_integrity_score": 1.00,
    "correction_grace_score": 0.80,
    "holistic_pillar_coverage_score": 0.55,
    "workflow_atom_accuracy_score": 0.90,
    "exception_and_edge_case_score": 0.45,
    "well_rounded_solution_score": 0.75,
    "constraint_and_hierarchy_discipline_score": 0.85,
    "epistemic_rigor_score": 0.45,
    "operational_reliability_score": 0.30
  },
  "diagnostic_coverage_breakdown": {
    "people_dimension_addressed": true,
    "process_dimension_addressed": true,
    "systems_dimension_addressed": true,
    "economics_dimension_addressed": false,
    "risk_dimension_addressed": false
  },
  "persona_experience_summary": "A new persona (Begur water-tanker supply) surfaced two real, previously-unreported, severe defects before the conversation could even begin: a committed regex bug that 500s on virtually any real opening message on the project's own required Python version, and a stale, untracked second .env file that silently shadows the root .env a user actually edits, plausibly explaining the team's own previously-logged 'persistent 401' incident. Once past those (patched in a disposable test copy only), the live conversational experience was fluent, well-paced, and handled two genuine corrections (billing ownership, a key-person risk) cleanly, correctly gating recommendations on a volunteered no-budget/non-technical constraint and declining Gen AI with sound reasoning both times. But the same systemic problems already logged from other personas reproduced again, with two new, sharper details: internal state shows a hardcoded 3-turn discovery cap overriding the architect's own logged 'missing financials' warning, and the fabricated-citation pattern escalated from an invented institutional report name to an invented statistic attributed to a real, named individual. The Evidence Ledger and geographic enrichment features were both completely inert throughout. And a correction-triggered resynthesis updated the report correctly behind the scenes while leaving the visible chat with literally no reply at all to the user's message.",
  "strengths": [
    "Real, live-verified: fluent, warm, single-question-at-a-time intake pacing across every turn.",
    "Real, live-verified: two simultaneous corrections (billing ownership, key-person risk) plus a new constraint (no budget/not tech-comfortable) were all folded cleanly into a full, accurate resynthesis with no contradictions or stale re-asks.",
    "Real, live-verified: sound, well-reasoned Tier 1/2/3 recommendation gating, correctly declining Gen AI twice with specific, non-generic reasoning tied to the actual problem shape.",
    "Real, live-verified: zero internal-label leakage across the entire session.",
    "Real, live-verified: most benchmark figures were explicitly and correctly hedged as external/unvalidated rather than presented as fact, despite real tool failures (Reddit/HackerNews 403s)."
  ],
  "coverage_gaps_and_regressions": [
    "NEW, CRITICAL: _generate_semantic_title crashes with an unhandled 500 on any real prompt over 35 characters, on the project's own required Python 3.11+ (committed at HEAD, not a local artifact).",
    "NEW, CRITICAL: a stale, untracked apps/api/.env silently shadows the root .env due to a relative env_file path resolved against CWD, directly reproducing the team's own previously-logged 'persistent 401' symptom; the resulting auth failure also still surfaces as a raw unhandled 500, not the graceful SessionStatus.FAILED the team's own spec requires.",
    "Reconfirmed a 4th time, now more severe: fabricated named citations, including one attributed to a real, identifiable named individual (Tomasz Tunguz) rather than only an invented institutional report title.",
    "NEW: the coverage-gap mechanism is now pinned down directly from state -- a hardcoded iterative_discovery.max_turns: 3 forces synthesis even after the architect's own confidence_reasons explicitly logged a missing required pillar.",
    "NEW: prompt caching is completely inactive in this live session (0 cache_read_tokens / 0 cache_creation_tokens across all 10 LLM calls), despite being the subject of the team's own active BS-10 remediation cycle.",
    "NEW: the Evidence Ledger stayed completely empty for the whole session despite substantial factual content being supplied across four turns.",
    "NEW: geographic_context stayed null despite a specific, real, named locality (Begur) being stated repeatedly.",
    "NEW: a correction-triggered resynthesis updated the report correctly server-side but appended no assistant reply to the visible chat at all -- a stronger regression than the previously-logged 'missing acknowledgment' finding.",
    "Reconfirmed a 3rd time: the sanitizer drops full substantive sentences (time pressure, value judgments), not just filler words.",
    "Reconfirmed, unchanged: no proactive budget/tech-comfort question; the user must volunteer it unprompted."
  ],
  "concrete_prompt_patches": [
    "Fix the (?i) inline-flag placement in _generate_semantic_title immediately -- this is a P0 production crash on the project's own required Python version, not a style nit.",
    "Resolve env_file relative to the repository root (or an explicit absolute path) rather than the process CWD, and/or delete or .gitignore-enforce against stray nested .env files, so a key rotation in the documented .env location always takes effect.",
    "Route unhandled exceptions in orchestrate() (regex crashes, provider auth errors alike) through the SessionStatus.FAILED path with sanitized failure metadata instead of letting them propagate as raw 500s.",
    "Remove the specific named-citation examples from the synthesis prompt entirely (including any real individual's name) -- now confirmed to reproduce verbatim or by close analogy across four unrelated live sessions.",
    "Gate synthesis on six-pillar completeness rather than a fixed max_turns cap, or at minimum let the architect's own 'missing pillar' confidence_reasons block synthesis when a pillar is flagged missing.",
    "Ensure a resynthesis triggered by a correction always appends a corresponding assistant chat message, even a short one, so the visible conversation never goes silent after a user's turn.",
    "Investigate why cache_read_tokens/cache_creation_tokens are 0 across a full live session -- verify the prompt-cache breakpoint is actually wired into the request path being exercised here.",
    "Investigate why evidence_ledger and geographic_context stayed inert this entire session despite clearly qualifying content (specific factual claims; a real, named locality)."
  ]
}
```
