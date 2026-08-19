"""Unit tests for the BuildSense local business tools.

Verifies input parsing, calculation accuracy, and security output wrapping
for search, economics calculator, and SOP parser tools.
"""

import json
from unittest.mock import patch, MagicMock
from app.mcp.tools import web_search_mcp, calculator_mcp, document_parser_mcp, market_signal_mcp


def test_web_search_mcp_containment_wrapping() -> None:
    """
    Checks that web search signals are correctly wrapped in untrusted output XML tags.

    Arguments:
        None

    Returns:
        None
    """
    query = "competitor pricing list"
    output = web_search_mcp(query)
    
    assert output.startswith('<untrusted_tool_output source="web_search">')
    assert output.endswith('</untrusted_tool_output>')
    assert query in output


def test_calculator_mcp_economic_ratios() -> None:
    """
    Checks calculation output properties for customer value and CAC limits.

    Arguments:
        None

    Returns:
        None
    """
    # 150 LTV, 30 CAC, 15 ARPU (healthy LTV:CAC = 5.0, payback = 2.0 months)
    output_str = calculator_mcp(ltv=150.0, cac=30.0, average_revenue_per_customer=15.0, gross_margin_percent=85.0)
    results = json.loads(output_str)

    assert results["ltv_cac_ratio"] == 5.0
    assert results["payback_months"] == 2.0
    assert results["gross_margin_ratio"] == 0.85
    assert results["is_economically_healthy"] is True


def test_calculator_mcp_unhealthy_economics() -> None:
    """
    Checks health flag defaults to False for bad LTV:CAC payback ratios.

    Arguments:
        None

    Returns:
        None
    """
    # 50 LTV, 40 CAC, 2.0 ARPU (ratio = 1.25, payback = 20 months - unhealthy)
    output_str = calculator_mcp(ltv=50.0, cac=40.0, average_revenue_per_customer=2.0)
    results = json.loads(output_str)

    assert results["is_economically_healthy"] is False


def test_document_parser_mcp_sop_lines() -> None:
    """
    Checks that unstructured process lines are correctly parsed into task steps.

    Arguments:
        None

    Returns:
        None
    """
    sop_lines = "Step 1: Fetch invoice sheets\nStep 2: Parse items\n• Send email report"
    output_str = document_parser_mcp(sop_lines)
    steps = json.loads(output_str)

    assert len(steps) == 3
    assert steps[0]["step_id"] == "1"
    assert steps[0]["description"] == "Fetch invoice sheets"
    assert steps[1]["step_id"] == "2"
    assert steps[1]["description"] == "Parse items"
    assert steps[2]["step_id"] == "3"
    assert steps[2]["description"] == "Send email report"
    assert steps[1]["depends_on"] == ["1"]


def test_market_signal_mcp_containment() -> None:
    """
    Verifies that the market signals tool wraps findings in standard untrusted XML boundaries.
    """
    with patch("app.mcp.tools.httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "title": "HN test story",
                    "url": "https://news.ycombinator.com/item?id=123",
                    "num_comments": 10,
                    "points": 20,
                    "objectID": "123"
                }
            ],
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Reddit test post",
                            "subreddit": "saas",
                            "num_comments": 5,
                            "score": 15,
                            "permalink": "/r/saas/comments/abc"
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        output = market_signal_mcp("saas marketing")
        assert output.startswith('<untrusted_tool_output source="market_signal">')
        assert output.endswith('</untrusted_tool_output>')
        assert "Real-time research signals found" in output
        assert "HN test story" in output
        assert "Reddit test post" in output

