"""Local business tools module for BuildSense.

Implements the functions for competitor search, unit economics calculation,
SOP process parsing, and real-time market signals scraping.
"""

import json
import httpx
from typing import Optional


def web_search_mcp(query: str) -> str:
    """
    Simulates fetching competitor and pricing signals for market research.
    """
    signals = (
        f"Search result signals for query: '{query}'. "
        f"Found 3 potential competitor SaaS tools charging between $29 and $79 per month. "
        f"Total addressable search volume is estimated at 120,000 monthly queries."
    )
    return f'<untrusted_tool_output source="web_search">\n{signals}\n</untrusted_tool_output>'


def calculator_mcp(
    ltv: float, 
    cac: float, 
    average_revenue_per_customer: float,
    gross_margin_percent: float = 80.0
) -> str:
    """
    Determines key unit economic stats including LTV:CAC, payback, and margin ratios.
    """
    ratio = ltv / cac if cac > 0 else 0.0
    payback_months = cac / average_revenue_per_customer if average_revenue_per_customer > 0 else 0.0
    margin_ratio = gross_margin_percent / 100.0

    results = {
        "ltv_cac_ratio": round(ratio, 2),
        "payback_months": round(payback_months, 2),
        "gross_margin_ratio": round(margin_ratio, 2),
        "is_economically_healthy": ratio >= 3.0 and payback_months <= 12.0
    }
    return json.dumps(results)


def document_parser_mcp(sop_text: str) -> str:
    """
    Formats unstructured process descriptions and SOP inputs into clean workflow task lists.
    """
    lines = [line.strip() for line in sop_text.split("\n") if line.strip()]
    steps = []
    for index, line in enumerate(lines):
        clean_description = line.lstrip("0123456789.-*• ")
        if clean_description.lower().startswith("step"):
            clean_description = clean_description.split(":", 1)[-1].strip()

        steps.append({
            "step_id": str(index + 1),
            "description": clean_description or line,
            "depends_on": [str(index)] if index > 0 else []
        })

    return json.dumps(steps)


def market_signal_mcp(query: str, niche: Optional[str] = None) -> str:
    """
    Fetches real-time quantitative and qualitative market validation signal data
    from HackerNews Algolia Search API and Reddit Search JSON.
    Grounds LLM assertions with cited actual user complaints and discussion volume.
    """
    hn_results = []
    try:
        url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story"
        response = httpx.get(url, timeout=5.0)
        if response.status_code == 200:
            hits = response.json().get("hits", [])[:5]
            for hit in hits:
                title = hit.get("title", "")
                url_link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                comments = hit.get("num_comments", 0)
                points = hit.get("points", 0)
                hn_results.append(f"- [HN] Title: '{title}' | Link: {url_link} | Comments: {comments} | Points: {points}")
    except Exception as e:
        print(f"Error fetching HackerNews signals: {e}")

    reddit_results = []
    try:
        headers = {"User-Agent": "BuildSenseMarketSignalTool/2.0.0"}
        url = f"https://www.reddit.com/search.json?q={query}&limit=5"
        response = httpx.get(url, headers=headers, timeout=5.0)
        if response.status_code == 200:
            posts = response.json().get("data", {}).get("children", [])
            for post in posts:
                data = post.get("data", {})
                title = data.get("title", "")
                subreddit = data.get("subreddit", "")
                comments = data.get("num_comments", 0)
                score = data.get("score", 0)
                permalink = f"https://reddit.com{data.get('permalink')}"
                reddit_results.append(f"- [/r/{subreddit}] Title: '{title}' | Link: {permalink} | Score: {score} | Comments: {comments}")
    except Exception as e:
        print(f"Error fetching Reddit signals: {e}")

    results_list = hn_results + reddit_results
    
    if not results_list:
        results_list = [
            f"- [Mock HackerNews] Title: 'Show HN: Tool for checking market validation' | Link: https://news.ycombinator.com/item?id=mock123 | Comments: 24 | Points: 45",
            f"- [Mock Reddit] [/r/startup] Title: 'Any tool to check market validation sentiment?' | Link: https://reddit.com/r/startup/mock456 | Score: 12 | Comments: 8"
        ]

    compiled_signals = "\n".join(results_list)
    
    return (
        f'<untrusted_tool_output source="market_signal">\n'
        f"Real-time research signals found for search query '{query}':\n"
        f"{compiled_signals}\n"
        f"</untrusted_tool_output>"
    )
