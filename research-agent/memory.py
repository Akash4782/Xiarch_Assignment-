"""
memory.py — SQLite-backed persistence layer for the Research Agent.

Stores every completed research query along with its sources and
generated report.  On subsequent identical queries the orchestrator
can skip the entire LLM pipeline and return the cached result
instantly.

Schema
------
searches
    id        INTEGER  PRIMARY KEY AUTOINCREMENT
    query     TEXT     NOT NULL   — original user query (case-insensitive lookup)
    timestamp TEXT     NOT NULL   — ISO-8601 datetime of when the search was run
    sources   TEXT     NOT NULL   — JSON array of source URLs
    summary   TEXT     NOT NULL   — full Markdown report
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = "searches.db"


def _init_db(conn: sqlite3.Connection) -> None:
    """Ensure the searches table exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            query     TEXT    NOT NULL,
            timestamp TEXT    NOT NULL,
            sources   TEXT    NOT NULL,
            summary   TEXT    NOT NULL
        )
    """)
    conn.commit()


def save_search(query: str, sources: list[str], summary: str) -> None:
    """
    Persist a completed research result to SQLite.

    Parameters
    ----------
    query   : The original user query string.
    sources : List of URLs that were used as sources.
    summary : The full Markdown report text.
    """
    with sqlite3.connect(DB_PATH) as conn:
        _init_db(conn)
        conn.execute(
            "INSERT INTO searches (query, timestamp, sources, summary) VALUES (?, ?, ?, ?)",
            (query, datetime.now().isoformat(), json.dumps(sources), summary),
        )
        conn.commit()


def find_past_search(query: str) -> dict | None:
    """
    Look up the most recent cached result for a query.

    Matching is case-insensitive.  Returns the most recent hit
    (by timestamp DESC) or None if no match is found.

    Parameters
    ----------
    query : The user query to look up.

    Returns
    -------
    dict with keys {query, timestamp, sources, summary} or None.
    """
    with sqlite3.connect(DB_PATH) as conn:
        _init_db(conn)
        row = conn.execute(
            """
            SELECT query, timestamp, sources, summary
            FROM   searches
            WHERE  LOWER(query) = LOWER(?)
            ORDER  BY timestamp DESC
            LIMIT  1
            """,
            (query,),
        ).fetchone()

    if row:
        return {
            "query":     row[0],
            "timestamp": row[1],
            "sources":   json.loads(row[2]),
            "summary":   row[3],
        }
    return None
