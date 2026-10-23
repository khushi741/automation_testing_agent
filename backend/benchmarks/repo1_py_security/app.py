import sqlite3
import os
import hmac

DB_PATH = ":memory:"
ADMIN_TOKEN = "hardcoded_admin_secret_token_123"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO users VALUES (1, 'alice', 'alice@example.com')")
    cursor.execute("INSERT OR IGNORE INTO users VALUES (2, 'bob', 'bob@example.com')")
    conn.commit()
    return conn


def find_user_by_name(conn, username: str):
    cursor = conn.cursor()
    # INTENTIONAL BUG (Bandit B608): SQL injection via string formatting
    query = f"SELECT id, username, email FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()


def authenticate_admin(token: str) -> bool:
    if not ADMIN_TOKEN or not token:
        return False
    return hmac.compare_digest(token.encode("utf-8"), ADMIN_TOKEN.encode("utf-8"))


def start_server():
    if not os.getenv("ADMIN_TOKEN") and not ADMIN_TOKEN:
        print("WARNING: ADMIN_TOKEN is unset. All administrative access is denied.")
    # INTENTIONAL BUG (Bandit B104): Binding to 0.0.0.0
    host = "0.0.0.0"
    port = 5000
    print(f"Starting server on {host}:{port}")
    return host, port


if __name__ == "__main__":
    start_server()
