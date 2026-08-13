"""Pytest configuration and fixtures for the BuildSense E2E evaluation suite.

Provides database and cache mocks, and implements custom terminal reporting
for scenario pass rates and latency tracking.
"""

import pytest
from unittest.mock import AsyncMock, patch

# Global list to accumulate scenario execution results
scenario_results = []

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test execution status and latency during the 'call' phase.
    """
    outcome = yield
    rep = outcome.get_result()
    
    # We only log results during the actual test run (call phase)
    if rep.when == "call":
        scenario_name = item.name
        # Clean up parametrized name format, e.g. test_scenario[Short Starter Chip] -> Short Starter Chip
        if "[" in scenario_name and scenario_name.endswith("]"):
            scenario_name = scenario_name.split("[")[1][:-1]
            
        scenario_results.append({
            "name": scenario_name,
            "status": rep.outcome.upper(),
            "latency": rep.duration
        })

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    Hook to print a custom E2E evaluation summary report at the end of the test run.
    """
    # Only print if we actually ran any evaluation scenarios
    if not scenario_results:
        return

    terminalreporter.write_line("")
    terminalreporter.write_sep("=", "E2E EVALUATION REPORT", bold=True)
    terminalreporter.write_line(f"{'SCENARIO NAME':<55} {'STATUS':<12} {'LATENCY (s)':<12}")
    terminalreporter.write_line("-" * 80)
    
    passed_count = 0
    total_count = len(scenario_results)
    total_latency = 0.0
    
    for res in scenario_results:
        name = res["name"]
        status = res["status"]
        latency = res["latency"]
        total_latency += latency
        
        terminalreporter.write(f"{name:<55} ")
        if status == "PASSED":
            passed_count += 1
            terminalreporter.write(f"{status:<12}", green=True)
        else:
            terminalreporter.write(f"{status:<12}", red=True)
        terminalreporter.write_line(f"{latency:.2f}s")
        
    terminalreporter.write_line("-" * 80)
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0.0
    terminalreporter.write_line(f"Overall Pass Rate: {pass_rate:.1f}% | Total Latency: {total_latency:.2f}s")
    terminalreporter.write_sep("=", "", bold=True)


@pytest.fixture(autouse=True)
def mock_postgres_and_redis():
    """
    Autouse fixture to mock database (postgres_client) and cache (redis_client) calls,
    preventing connections to external databases and ensuring tests run fully in-memory.
    """
    from app.db.postgres import postgres_client
    from app.db.redis import redis_client

    # Define mock returns for projects and companies to populate company context
    async def mock_get_project(session_id):
        return {
            "session_id": session_id,
            "company_id": "mock-company-id",
            "title": "Mock Project",
            "mode": "OPTIMIZER"
        }

    async def mock_get_company(company_id):
        return {
            "id": company_id,
            "name": "Target Company",
            "industry_vertical": "Logistics",
            "industry": "Logistics",
            "core_tools": "Spreadsheets and email"
        }

    with patch.object(postgres_client, "save_session_state", AsyncMock()) as mock_save_state, \
         patch.object(postgres_client, "update_project_mode_and_title", AsyncMock()) as mock_update_title, \
         patch.object(postgres_client, "get_project", AsyncMock(side_effect=mock_get_project)) as mock_get_proj, \
         patch.object(postgres_client, "get_company", AsyncMock(side_effect=mock_get_company)) as mock_get_comp, \
         patch.object(postgres_client, "save_graph", AsyncMock()) as mock_save_gr, \
         patch.object(redis_client, "increment_global_spend", AsyncMock(return_value=0.025)) as mock_redis:
        
        yield {
            "save_session_state": mock_save_state,
            "update_project_mode_and_title": mock_update_title,
            "get_project": mock_get_proj,
            "get_company": mock_get_comp,
            "save_graph": mock_save_gr,
            "redis_increment_spend": mock_redis
        }
