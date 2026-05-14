import sqlite3

DB_NAME = "users.db"


def connect():
    return sqlite3.connect(DB_NAME)


def create_table():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT
    )
    """)

    conn.commit()
    conn.close()


def add_user(user_id, username):
    conn = connect()
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        # Update existing user
        cursor.execute(
            "UPDATE users SET username = ? WHERE user_id = ?",
            (username, user_id),
        )
    else:
        # Insert new user
        cursor.execute(
            """
    INSERT INTO users (user_id, username)
    VALUES (?, ?)
    """,
            (user_id, username),
        )

    conn.commit()
    conn.close()


def get_users():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    data = cursor.fetchall()

    conn.close()
    return data
