import sqlite3
import json
import os

from datetime import datetime, timezone
from contextlib import closing
from flask import current_app
from app.config import Config


def get_database_path():
    try:
        return current_app.config.get(
            "DATABASE_PATH",
            Config.DATABASE_PATH
        )
    except RuntimeError:
        return Config.DATABASE_PATH


def get_connection(database_path=None):

    database_path = database_path or get_database_path()

    if database_path != ":memory:":
        directory = os.path.dirname(database_path)

        if directory:
            os.makedirs(directory, exist_ok=True)

    return sqlite3.connect(
        database_path,
        timeout=10
    )


def initialize_database(database_path=None):

    with closing(get_connection(database_path)) as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_text TEXT NOT NULL,
                claims TEXT NOT NULL,
                results TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        connection.commit()


def save_analysis(input_text, claims, results):

    with closing(get_connection()) as connection:

        cursor = connection.execute("""
            INSERT INTO analyses (
                input_text,
                claims,
                results,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            input_text,
            json.dumps(claims),
            json.dumps(results),
            datetime.now(timezone.utc).isoformat()
        ))

        analysis_id = cursor.lastrowid

        connection.commit()

        return analysis_id


def get_all_analyses(limit=20):

    with closing(get_connection()) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT id, input_text, claims, created_at
            FROM analyses
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [
            {
                "id": row["id"],
                "input_text": row["input_text"],
                "claims": json.loads(row["claims"]),
                "created_at": row["created_at"]
            }
            for row in rows
        ]


def get_analysis_by_id(analysis_id):

    with closing(get_connection()) as connection:

        connection.row_factory = sqlite3.Row

        row = connection.execute("""
            SELECT *
            FROM analyses
            WHERE id = ?
        """, (analysis_id,)).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "input_text": row["input_text"],
            "claims": json.loads(row["claims"]),
            "results": json.loads(row["results"]),
            "created_at": row["created_at"]
        }