import sqlite3

DATABASE_NAME = "kollinksnap.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row

    return connection


def create_table():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS links (
                short_code TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0
            )
        """)

        connection.commit()

    finally:
        connection.close()


if __name__ == "__main__":
    create_table()
    print("Database and table are ready!")