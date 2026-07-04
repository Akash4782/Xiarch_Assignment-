"""
agent.py — Agentic LLM loop for the Autonomous Research Agent.

The agent runs an iterative tool-calling loop powered by Groq's
function-calling API.  In each iteration:
  - The LLM decides which tools to call (web_search or fetch_page).
  - All tool calls in a single iteration are executed in parallel.
  - Results are fed back to the LLM as tool messages.
  - The loop terminates when the LLM stops calling tools or when
    max_iterations is reached.
"""

import os
import json
import asyncio
import aiohttp
from groq import Groq
from dotenv import load_dotenv

from tools.search import web_search
from tools.extract import fetch_page_async

load_dotenv()

# Singleton Groq client
_client: Groq | None = None


def get_client() -> Groq:
    """Return (or lazily create) a singleton Groq client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set. "
                "Get a free key at https://console.groq.com"
            )
        _client = Groq(api_key=api_key)
    return _client


# Tool schema definitions passed to the Groq API
_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for a query and return top results "
                "with titles, URLs, and preview snippets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": (
                "Fetch and extract clean, readable text content from a given URL. "
                "Use this after web_search to read the full content of a page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL of the page to fetch",
                    }
                },
                "required": ["url"],
            },
        },
    },
]

_SYSTEM_PROMPT = (
    "You are an autonomous research agent with access to two tools: web_search and fetch_page.\n\n"
    "CRITICAL GUIDELINES:\n"
    "1. Always start by calling `web_search` to find relevant sources.\n"
    "2. Once you get search results, you MUST call `fetch_page` on the most promising/relevant URLs to get the full page content. Do not just keep searching. You need to fetch and read the actual pages to compile a detailed report!\n"
    "3. Only stop and finish when you have successfully fetched and read the content of multiple sources.\n"
    "4. If you have enough information, stop calling tools."
)

# Model used for the agentic tool-calling loop.
# Requirements: must support OpenAI-style function/tool calling via the Groq API.
# - qwen/qwen3.6-27b  → current production model with reliable tool-call support
# - DO NOT use llama-3.3-70b-versatile  → emits <function=...> tags, not tool_calls JSON
# - DO NOT use llama3-groq-70b-8192-tool-use-preview → decommissioned Jan 2025
_TOOL_USE_MODEL = "qwen/qwen3.6-27b"


async def run_agent(user_query: str, max_iterations: int = 6) -> tuple[set[str], list[str]]:
    """
    Run the autonomous agentic loop for the given research query.

    Parameters
    ----------
    user_query : str
        The research topic or question from the user.
    max_iterations : int
        Maximum number of LLM ↔ tool round-trips before stopping.

    Returns
    -------
    gathered_sources : set[str]
        All URLs that were fetched during the research.
    gathered_text : list[str]
        Extracted text content from each fetched page.
    """
    c = get_client()

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    gathered_sources: set[str] = set()
    gathered_text: list[str] = []

    print(f"[*] Starting research for: {user_query}")

    for iteration in range(max_iterations):
        print(f"[*] Iteration {iteration + 1}/{max_iterations}")

        response = c.chat.completions.create(
            model=_TOOL_USE_MODEL,
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )

        response_message = response.choices[0].message

        if not response_message.tool_calls:
            # LLM is done — no more tool calls requested
            print("[*] Agent finished gathering information.")
            if response_message.content:
                messages.append(response_message)
            break

        print(f"[*] Agent requested {len(response_message.tool_calls)} tool call(s).")
        messages.append(response_message)

        # ── Execute all tool calls in parallel ────────────────────────────
        async with aiohttp.ClientSession() as session:
            tasks: list[tuple[str, asyncio.Future, str]] = []
            loop = asyncio.get_event_loop()

            for call in response_message.tool_calls:
                func_name = call.function.name
                try:
                    args = json.loads(call.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}

                if func_name == "web_search":
                    query_arg = args.get("query", "")
                    print(f"  → web_search: {query_arg!r}")
                    tasks.append(
                        (call.id, loop.run_in_executor(None, web_search, query_arg), func_name)
                    )

                elif func_name == "fetch_page":
                    url_arg = args.get("url", "")
                    print(f"  → fetch_page: {url_arg}")
                    gathered_sources.add(url_arg)
                    tasks.append(
                        (call.id, fetch_page_async(url_arg, session), func_name)
                    )

            # Await all tasks
            results: list[tuple[str, object, str]] = []
            for call_id, task, func_name in tasks:
                try:
                    result = await task
                    results.append((call_id, result, func_name))
                except Exception as exc:
                    results.append((call_id, f"Error: {exc}", func_name))

        # ── Append tool results back to the conversation ───────────────────
        for call_id, result, func_name in results:
            if func_name == "fetch_page" and isinstance(result, tuple):
                url, text = result
                result_str = text
                gathered_text.append(text)
            elif func_name == "web_search":
                result_str = str(result)
                # Keep search snippets as fallback source text in case fetch_page fails or is skipped
                gathered_text.append(result_str)
            else:
                result_str = str(result)

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": func_name,
                "content": result_str,
            })

    return gathered_sources, gathered_text
