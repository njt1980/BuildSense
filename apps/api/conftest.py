"""Pytest configuration hooks for BuildSense evaluations and testing.

Registers the --run-evals CLI option and handles skip marks logic for
expensive agentic evaluation test runs.
"""

from typing import List
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Registers a custom --run-evals command line flag for pytest.

    Arguments:
        parser: The pytest command-line parser object.

    Returns:
        None
    """
    parser.addoption(
        "--run-evals",
        action="store_true",
        default=False,
        help="Execute the LLM-as-a-judge evaluations test cases",
    )


def pytest_configure(config: pytest.Config) -> None:
    """
    Registers the 'evals' test marker inside pytest.

    Arguments:
        config: The pytest configuration object.

    Returns:
        None
    """
    config.addinivalue_line(
        "markers",
        "evals: Mark a test as an agentic evaluation (run-evals)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: List[pytest.Item]) -> None:
    """
    Filters test execution collection, skipping evals unless --run-evals is specified.

    Arguments:
        config: The active pytest configuration.
        items: List of collected test items.

    Returns:
        None
    """
    if config.getoption("--run-evals"):
        # Do not skip if explicit option is supplied
        return

    skip_marker = pytest.mark.skip(reason="Requires the --run-evals flag to execute LLM evaluations.")
    for test_item in items:
        if "evals" in test_item.keywords:
            test_item.add_marker(skip_marker)
