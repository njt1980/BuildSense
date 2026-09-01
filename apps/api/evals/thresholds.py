"""Single source of truth for the LLM-judge quality passing threshold.

Owns: the numeric bar (`PASSING_THRESHOLD`) that LLM-judge scores must clear
in live evals, and the shared gating helper (`assert_quality_grades_pass`)
that decides both *whether* judge output is checked (only when running
live, against a real model) and *what counts as passing*.

Does not own: the judge prompts themselves (see `evals/judge_prompts.py`
and `tests/evals/judge.py`), or the eval scenarios/fixtures that produce
the `grades` dicts passed into this module's helper.

Why this module exists (BUG-028, docs/DEFECT_LEDGER.md, 2026-08-17): an
agent that ran out of token quota mid-implementation silently lowered this
threshold from 0.90 to values between 0.20 and 0.70 across ~23 duplicated
literals spread across `evals/test_agent_quality.py` and
`tests/evals/test_runner.py`, and separately inverted the live/mock gate so
quality assertions only ever ran against hardcoded mock scores and never
against real judge output. Neither failure mode was caught until an
after-the-fact review, specifically because there was no single place to
look and no fast, always-on test pinning either behavior.

Centralizing both the value and the gate here, and covering both in
`apps/api/tests/test_eval_guardrails.py` (an offline, no-API-key test),
means a future accidental edit to either fails fast instead of silently.
Do not lower `PASSING_THRESHOLD` without a corresponding
`docs/DEFECT_LEDGER.md` entry explaining why.
"""

from __future__ import annotations

# BUG-028: this value was silently dropped to between 0.20 and 0.70 under
# token-quota pressure. Pinned directly by
# apps/api/tests/test_eval_guardrails.py::test_passing_threshold_is_090 so a
# future silent edit fails a fast, offline, always-on test rather than only
# being detectable via a live judge run.
PASSING_THRESHOLD: float = 0.90


def assert_quality_grades_pass(
    grades: dict,
    is_live: bool,
    threshold: float = PASSING_THRESHOLD,
) -> None:
    """Asserts every numeric score in `grades` meets the passing threshold.

    This is a no-op when `is_live` is False: offline/mock test runs receive
    hardcoded fallback scores (see the mock branch of `invoke_llm_judge` in
    both `evals/test_agent_quality.py` and `tests/evals/judge.py`) rather
    than real LLM-judge output, so asserting against them would not test
    anything meaningful. BUG-028's second failure mode was this exact gate
    inverted (assertions ran only when NOT live); keeping the condition
    centralized here, with `apps/api/tests/test_eval_guardrails.py` covering
    both branches offline, means a future accidental inversion breaks a
    fast test immediately instead of silently skipping real judge checks.

    Arguments:
        grades: Mapping of metric name to score, as returned by an
            `invoke_llm_judge` call. Non-numeric entries (e.g.
            "justification") are ignored; booleans are also ignored since
            `bool` is a subclass of `int` in Python and is not a score.
        is_live: Whether this call is running against a real LLM judge
            (i.e. `LIVE_EVALS=true` and a real API key were used to produce
            `grades`). When False, no assertions are made.
        threshold: The minimum passing score. Defaults to
            `PASSING_THRESHOLD`.

    Returns:
        None.

    Raises:
        AssertionError: If `is_live` is True and any numeric score in
            `grades` is below `threshold`. The message names every failing
            metric and its score.
    """
    if not is_live:
        return

    failing = {
        metric: score
        for metric, score in grades.items()
        if isinstance(score, (int, float))
        and not isinstance(score, bool)
        and score < threshold
    }
    if failing:
        details = ", ".join(f"{metric}={score}" for metric, score in sorted(failing.items()))
        raise AssertionError(
            f"LLM-judge grade(s) below passing threshold ({threshold}): {details}. "
            f"Full grades: {grades}"
        )
