"""Pytest configuration hooks for BuildSense evaluations and testing.

Registers the --run-evals CLI option and handles skip marks logic for
expensive agentic evaluation test runs.
"""

from typing import List
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Registers custom command line flags for BuildSense pytest runs.
    """
    parser.addoption(
        "--run-evals",
        action="store_true",
        default=False,
        help="Execute the LLM-as-a-judge evaluations test cases",
    )
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Execute E2E evaluation scenarios using the live Anthropic API",
    )
    parser.addoption(
        "--live-model",
        action="store",
        default="claude-haiku-4-5-20251001",
        help="Model to use for orchestrator node execution during live runs",
    )


def pytest_configure(config: pytest.Config) -> None:
    """
    Registers the 'evals' test marker and populates live evaluation environment variables.
    """
    config.addinivalue_line(
        "markers",
        "evals: Mark a test as an agentic evaluation (run-evals)"
    )
    # Propagate flags to environment variables for visibility within tests
    import os
    os.environ["LIVE_EVALS"] = "true" if config.getoption("--live") else "false"
    os.environ["LIVE_EVALS_MODEL"] = str(config.getoption("--live-model"))


def pytest_collection_modifyitems(config: pytest.Config, items: List[pytest.Item]) -> None:
    """
    Filters test execution collection, skipping evals unless --run-evals is specified.
    """
    if config.getoption("--run-evals"):
        # Do not skip if explicit option is supplied
        return

    skip_marker = pytest.mark.skip(reason="Requires the --run-evals flag to execute LLM evaluations.")
    for test_item in items:
        if "evals" in test_item.keywords:
            test_item.add_marker(skip_marker)
