import sqlite3

DB_NAME = "database.db"


# ---------------- CREATE TABLE ----------------
def create_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------------- ADD USER NAME ----------------
def add_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username)
    )

    conn.commit()
    conn.close()


# ---------------- GET ALL USERS ----------------
def get_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, user_id, username
        FROM users
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


# ---------------- DELETE NAME ----------------
def delete_name(row_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE id = ?", (row_id,))

    conn.commit()
    conn.close()


# ---------------- UPDATE NAME ----------------
def update_name(row_id, new_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET username = ? WHERE id = ?", (new_name, row_id))

    conn.commit()
    conn.close()


# Setting table
def create_settings_table():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()


def set_value(key, value):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO settings (key, value)
        VALUES (?, ?)
    """, (key, value))

    conn.commit()
    conn.close()
