
import os
import sqlite3

import psycopg
from psycopg.rows import dict_row


DATABASE_NAME = "kollinksnap.db"
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Connect to Neon PostgreSQL or local SQLite."""
    if DATABASE_URL:
        return psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row,
        )

    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def execute_query(connection, query, parameters=()):
    """Execute a query using the placeholder syntax for its database."""
    if isinstance(connection, sqlite3.Connection):
        query = query.replace("%s", "?")

    return connection.execute(query, parameters)


def create_table():
    connection = get_connection()

    try:
        execute_query(
            connection,
            """
            CREATE TABLE IF NOT EXISTS links (
                short_code TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0
            )
            """,
        )

        connection.commit()

    finally:
        connection.close()


if __name__ == "__main__":
    create_table()
    print("Database and table are ready!")
