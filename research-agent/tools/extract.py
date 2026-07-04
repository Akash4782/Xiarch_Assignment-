"""
tools/extract.py — Web page fetching and text extraction tool.

Provides both a synchronous and an asynchronous implementation
for fetching web pages and extracting their clean, readable text
content using trafilatura (removes ads, navigation, boilerplate, etc.).

The async version (fetch_page_async) is used by the agent loop to
fetch multiple pages in parallel within a single aiohttp ClientSession,
significantly reducing overall research time.

Note: Content is truncated to 2 000 characters per page to stay within
Groq's free-tier token-per-minute (TPM) limits.
"""

import aiohttp
import trafilatura

# Keep individual page content within Groq's free-tier TPM budget.
_MAX_CHARS_PER_PAGE = 2_000


def fetch_page_sync(url: str) -> str:
    """
    Fetch and extract readable text from a URL (synchronous).

    Parameters
    ----------
    url : The full URL of the page to fetch.

    Returns
    -------
    Extracted text content, or an error/fallback message.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                return text[:_MAX_CHARS_PER_PAGE]
        return f"Could not extract readable content from: {url}"
    except Exception as exc:
        return f"Error fetching {url}: {exc}"


async def fetch_page_async(url: str, session: aiohttp.ClientSession) -> tuple[str, str]:
    """
    Fetch and extract readable text from a URL (asynchronous).

    Designed to run concurrently inside an aiohttp ClientSession,
    enabling multiple pages to be fetched in parallel within a
    single agent iteration.

    Parameters
    ----------
    url     : The full URL of the page to fetch.
    session : An active aiohttp.ClientSession to reuse for the request.

    Returns
    -------
    Tuple of (url, extracted_text).  On failure, extracted_text contains
    an error description rather than raising an exception, so the agent
    loop can continue gracefully.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
            html = await response.text(errors="replace")
            text = trafilatura.extract(html)
            if text:
                return url, text[:_MAX_CHARS_PER_PAGE]
            return url, f"Could not extract readable content from: {url}"
    except Exception as exc:
        return url, f"Error fetching {url}: {exc}"
