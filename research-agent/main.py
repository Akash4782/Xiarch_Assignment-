"""
main.py — Orchestrator for the Autonomous Research Agent.

Flow:
  1. Accept a research query (CLI argument or interactive prompt).
  2. Check SQLite memory for a cached result.
  3. If no cache hit, run the agentic search loop.
  4. Chunk and semantically deduplicate the gathered text.
  5. Synthesize a structured Markdown report via Groq LLM.
  6. Export to Markdown (and optionally PDF).
  7. Persist the result to SQLite memory.
"""

import asyncio
import argparse
import sys
import os

from dotenv import load_dotenv
load_dotenv()

from agent import run_agent, get_client
from dedup import chunk_text, deduplicate
from export import export_markdown, export_pdf
from memory import find_past_search, save_search


# Synthesis uses a high-quality general-purpose model (no tool calling here).
# openai/gpt-oss-120b is Groq's recommended replacement for llama-3.3-70b-versatile (deprecated Aug 2026).
_SYNTHESIS_MODEL = "openai/gpt-oss-120b"

# ──────────────────────────────────────────────
# Report Synthesis
# ──────────────────────────────────────────────

async def synthesize_report(query: str, deduplicated_text: list[str], sources: list[str]) -> str:
    """
    Ask the Groq LLM to produce a structured research report
    from the deduplicated source text.

    Retries up to 4 times with exponential back-off on rate-limit
    or service unavailability errors.
    """
    print("[*] Generating final synthesis report with Groq...")

    combined_text = "\n\n".join(deduplicated_text)

    prompt = f"""
You are a research analyst. Based on the following gathered source material,
produce a structured report with these exact sections:

## Executive Summary
## Key Points
## Important Findings
## References / Sources
## Actionable Insights

Source material:
{combined_text}

Query: {query}

Make sure to include the actual URLs from the provided sources in the References section.
URLs: {", ".join(sources)}
"""

    c = get_client()

    for attempt in range(4):
        try:
            response = c.chat.completions.create(
                model=_SYNTHESIS_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            if "503" in str(e) or "429" in str(e):
                wait_time = 2 ** attempt
                print(f"  [~] Groq API busy ({e}). Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

    return "[!] Synthesis failed due to repeated API errors."


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

async def main():
    # Validate environment
    if not os.environ.get("GROQ_API_KEY"):
        print("[!] GROQ_API_KEY not found. Please add it to your .env file.")
        print("    Get a free key at: https://console.groq.com")
        sys.exit(1)

    # ── Argument parsing ──────────────────────
    parser = argparse.ArgumentParser(
        description="Autonomous Research Agent — powered by Groq + DuckDuckGo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Latest AI coding agents in 2025"
  python main.py "quantum computing trends" --force
  python main.py                          # interactive mode
        """,
    )
    parser.add_argument(
        "query",
        type=str,
        nargs="?",
        default=None,
        help="Research topic or question (omit for interactive prompt)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force a fresh search even if memory already has this query",
    )
    args = parser.parse_args()

    # ── Interactive fallback if no query given ─
    query = args.query
    if not query:
        print("=" * 60)
        print("       Autonomous Research Agent")
        print("=" * 60)
        query = input("Enter your research topic: ").strip()
        if not query:
            print("[!] No query provided. Exiting.")
            sys.exit(1)
        print()

    # ── Memory check ──────────────────────────
    if not args.force:
        past = find_past_search(query)
        if past:
            print(f"[*] Found cached research from {past['timestamp']}")
            print(f"[*] Sources used: {len(past['sources'])}")
            print("[*] Returning cached report (use --force to re-research):")
            print("=" * 60)
            print(past["summary"])
            return

    # ── Agentic search loop ───────────────────
    try:
        sources, gathered_text = await run_agent(query)
    except Exception as e:
        print(f"[!] Error during research phase: {e}")
        sys.exit(1)

    if not gathered_text:
        print("[!] No text could be gathered for the query. Try rephrasing.")
        sys.exit(1)

    # ── Deduplication ─────────────────────────
    print(f"[*] Gathered {len(gathered_text)} articles. Chunking and deduplicating...")
    all_chunks = []
    for text in gathered_text:
        all_chunks.extend(chunk_text(text))

    print(f"[*] Chunks before deduplication: {len(all_chunks)}")
    unique_chunks = deduplicate(all_chunks)
    print(f"[*] Chunks after  deduplication: {len(unique_chunks)}")

    # ── Report synthesis ──────────────────────
    final_report = await synthesize_report(query, unique_chunks, list(sources))

    # ── Export ────────────────────────────────
    os.makedirs("reports", exist_ok=True)
    safe_query = "".join(c if c.isalnum() or c in (" ", "-") else "_" for c in query)
    safe_query = safe_query.replace(" ", "_")[:60]

    md_file = os.path.join("reports", f"report_{safe_query}.md")
    pdf_file = os.path.join("reports", f"report_{safe_query}.pdf")

    export_markdown(final_report, md_file)
    export_pdf(final_report, pdf_file)

    # ── Persist to memory ─────────────────────
    save_search(query, list(sources), final_report)

    print()
    print("=" * 60)
    print(f"  ✓ Research complete!")
    print(f"  ✓ Report saved to: {md_file}")
    print(f"  ✓ PDF version saved to: {pdf_file}")
    print(f"  ✓ Memory updated: this query is now cached in SQLite")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
