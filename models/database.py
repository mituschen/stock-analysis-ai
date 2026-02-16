"""Database helpers for storing run and prompt results.

This module uses SQLite via the standard `sqlite3` module for simplicity.
If you wish to use another database (PostgreSQL, MySQL, etc.), replace
the connection and table creation code accordingly.
"""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "results.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)



def _connect() -> sqlite3.Connection:
    """Return a new connection to the SQLite database.

    The connection uses row factory to return dictionary-like rows.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



def init_db() -> None:
    """Initialize the database tables if they don't exist."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                context_json TEXT,
                started_at TEXT,
                finished_at TEXT,
                average_score REAL,
                final_rating TEXT,
                final_target_price REAL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                prompt_id TEXT NOT NULL,
                prompt_version INTEGER,
                prompt_name TEXT,
                score INTEGER,
                rating TEXT,
                target_buy_price REAL,
                rationale TEXT,
                raw_response TEXT,
                created_at TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );
            """
        )
        conn.commit()


@contextmanager
def get_connection():
    """Provide a context manager for database connections."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def start_run(ticker: str, context_json: str) -> str:
    """Insert a new run and return its UUID.

    Args:
        ticker: The stock symbol being analysed.
        context_json: JSON representation of the context passed to prompts.

    Returns:
        The generated run_id (a UUID string).
    """
    run_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO runs (run_id, ticker, context_json, started_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, ticker, context_json, started_at),
        )
    return run_id


def finish_run(
    run_id: str,
    average_score: float,
    final_rating: str,
    final_target_price: float,
) -> None:
    """Update a run row when analysis completes."""
    finished_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE runs
            SET finished_at = ?, average_score = ?, final_rating = ?, final_target_price = ?
            WHERE run_id = ?
            """,
            (finished_at, average_score, final_rating, final_target_price, run_id),
        )


def save_prompt_result(
    run_id: str,
    prompt_id: str,
    prompt_version: int,
    prompt_name: str,
    score: int,
    rating: str,
    target_buy_price: float,
    rationale: str,
    raw_response: str,
) -> None:
    """Insert a row into `prompt_results` for a single prompt invocation."""
    created_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO prompt_results (
                run_id, prompt_id, prompt_version, prompt_name,
                score, rating, target_buy_price, rationale, raw_response, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                prompt_id,
                prompt_version,
                prompt_name,
                score,
                rating,
                target_buy_price,
                rationale,
                raw_response,
                created_at,
            ),
        )


def get_prompt_results(run_id: str):
    """Return all prompt results for a given run_id."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM prompt_results WHERE run_id = ? ORDER BY id ASC",
            (run_id,),
        )
        return [dict(row) for row in cur.fetchall()]
