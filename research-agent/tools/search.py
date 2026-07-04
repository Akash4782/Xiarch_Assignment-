"""
tools/search.py — Web search tool for the Research Agent.

Wraps the DuckDuckGo search library to provide a simple text-search
function that the Groq LLM can invoke as a tool call.

No API key required — DuckDuckGo is free and unauthenticated.
"""

from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo and return formatted results.

    Each result includes its title, URL, and a short preview snippet.
    The output is a plain-text string formatted for easy LLM consumption.

    Parameters
    ----------
    query       : The search query string.
    max_results : Maximum number of results to return (default: 5).

    Returns
    -------
    Formatted string of results, or an error message on failure.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for query: {query!r}"

        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            href  = r.get("href", "")
            body  = r.get("body", "No snippet available")
            lines.append(f"[{i}] {title}\n    URL: {href}\n    Preview: {body}\n")

        return "\n".join(lines)

    except Exception as exc:
        return f"Search error for {query!r}: {exc}"
