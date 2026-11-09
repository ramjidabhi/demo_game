"""
Database module for the Game App.
Handles SQLite connection, schema creation, match history recording,
leaderboard queries, and aggregate statistics.
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional

# Use SQLITE_PATH when configured (Docker / Kubernetes).
# Otherwise, keep the database beside this Python file.
DEFAULT_DB_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "game_history.db"
)

DB_FILE = os.path.abspath(
    os.path.expanduser(
        os.environ.get("SQLITE_PATH") or DEFAULT_DB_FILE
    )
)


def get_connection() -> sqlite3.Connection:
    """Create a SQLite connection and ensure its directory exists."""
    db_directory = os.path.dirname(DB_FILE)

    if db_directory:
        os.makedirs(db_directory, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the database schema if it doesn't already exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                game_mode TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                score INTEGER NOT NULL,
                apples_eaten INTEGER DEFAULT 0,
                duration_seconds REAL NOT NULL,
                result TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_score ON game_history(score DESC);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON game_history(timestamp DESC);"
        )

        conn.commit()


def insert_game(
    player_name: str,
    game_mode: str,
    difficulty: str,
    score: int,
    apples_eaten: int,
    duration_seconds: float,
    result: str = "Game Over"
) -> Dict[str, Any]:
    """Insert a completed game record and check if it achieved a new high score."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT MAX(score) as high_score FROM game_history")
        row = cursor.fetchone()

        previous_high = (
            row["high_score"]
            if row and row["high_score"] is not None
            else 0
        )

        is_new_high = score > previous_high and score > 0

        cursor.execute("""
            INSERT INTO game_history
            (player_name, game_mode, difficulty, score, apples_eaten,
             duration_seconds, result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            player_name.strip() or "Player 1",
            game_mode,
            difficulty,
            int(score),
            int(apples_eaten),
            round(float(duration_seconds), 1),
            result
        ))

        conn.commit()
        game_id = cursor.lastrowid

        return {
            "id": game_id,
            "is_new_high": is_new_high,
            "previous_high": previous_high,
            "current_score": score
        }


def get_history(
    limit: int = 50,
    mode: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve recent game history with optional game_mode filter."""
    with get_connection() as conn:
        cursor = conn.cursor()

        if mode and mode.lower() != "all":
            cursor.execute("""
                SELECT id, player_name, game_mode, difficulty, score,
                       apples_eaten, duration_seconds, result,
                       datetime(timestamp, 'localtime') as formatted_time
                FROM game_history
                WHERE LOWER(game_mode) = LOWER(?)
                ORDER BY id DESC
                LIMIT ?
            """, (mode, limit))
        else:
            cursor.execute("""
                SELECT id, player_name, game_mode, difficulty, score,
                       apples_eaten, duration_seconds, result,
                       datetime(timestamp, 'localtime') as formatted_time
                FROM game_history
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve all-time highest scores."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, player_name, game_mode, difficulty, score,
                   apples_eaten, duration_seconds,
                   datetime(timestamp, 'localtime') as formatted_time
            FROM game_history
            ORDER BY score DESC, duration_seconds ASC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_stats() -> Dict[str, Any]:
    """Retrieve summary statistics for the dashboard."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_games,
                COALESCE(MAX(score), 0) as high_score,
                COALESCE(AVG(score), 0) as avg_score,
                COALESCE(SUM(apples_eaten), 0) as total_apples,
                COALESCE(SUM(duration_seconds), 0) as total_seconds
            FROM game_history
        """)

        row = cursor.fetchone()

        cursor.execute("""
            SELECT game_mode, COUNT(*) as count
            FROM game_history
            GROUP BY game_mode
            ORDER BY count DESC
            LIMIT 1
        """)

        mode_row = cursor.fetchone()
        fav_mode = mode_row["game_mode"] if mode_row else "Classic"

        return {
            "total_games": row["total_games"],
            "high_score": row["high_score"],
            "avg_score": round(row["avg_score"], 1),
            "total_apples": row["total_apples"],
            "total_seconds": round(row["total_seconds"], 1),
            "favorite_mode": fav_mode
        }


def clear_history() -> bool:
    """Clear all records from game_history."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM game_history;")
        cursor.execute(
            "DELETE FROM sqlite_sequence WHERE name='game_history';"
        )

        conn.commit()
        return True


if __name__ == "__main__":
    init_db()

    print("Database initialized successfully at:", DB_FILE)
    print("Stats:", get_stats())
