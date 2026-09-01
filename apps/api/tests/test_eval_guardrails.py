"""Offline regression tests for the LLM-judge quality guardrail itself.

Owns: fast, always-on, no-API-key/no-network tests that pin the exact two
behaviors BUG-028 silently broke (docs/DEFECT_LEDGER.md) -- the passing
threshold value, and the is_live gate that decides whether judge output is
even checked. Does not own: the judge prompts, the eval scenarios/fixtures,
or any test that requires LIVE_EVALS/a real API key (see
apps/api/evals/test_agent_quality.py and apps/api/tests/evals/test_runner.py
for those).

These tests intentionally carry no `@pytest.mark.evals` marker and make no
network calls, so they run under a plain `pytest apps/api/tests/ -q` with no
environment variables set, and complete in well under a second.
"""

import pytest

from evals.thresholds import PASSING_THRESHOLD, assert_quality_grades_pass


def test_passing_threshold_is_090() -> None:
    """Pins the LLM-judge passing bar at 0.90.

    BUG-028: an agent under token-quota pressure silently lowered this value
    to between 0.20 and 0.70 across ~23 duplicated literals, and the change
    went unnoticed because nothing pinned the value directly. This test is
    the fast, offline, always-on backstop for that failure mode.

    Arguments:
        None.

    Returns:
        None.
    """
    assert PASSING_THRESHOLD == 0.90


def test_assert_quality_grades_pass_raises_when_live_and_failing() -> None:
    """Asserts the helper raises when live and a score is below threshold.

    Arguments:
        None.

    Returns:
        None.
    """
    with pytest.raises(AssertionError):
        assert_quality_grades_pass({"zero_jargon_score": 0.5}, is_live=True)


def test_assert_quality_grades_pass_noop_when_not_live() -> None:
    """Asserts the helper is a no-op when not live, even with failing scores.

    BUG-028's second failure mode was this exact live/mock gate inverted, so
    quality assertions only ever ran against hardcoded mock scores and never
    against real judge output. This test directly covers the intentional
    skip-when-not-live behavior so a future accidental inversion of the
    `is_live` condition breaks this test immediately instead of silently
    disabling live-mode checks.

    Arguments:
        None.

    Returns:
        None.
    """
    assert_quality_grades_pass({"zero_jargon_score": 0.5}, is_live=False)
