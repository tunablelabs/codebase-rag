import sqlite3
import json
from datetime import datetime

local_response_db = "local_user_database.db"

def check_and_create_table():
    with sqlite3.connect(local_response_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_data (
                user_id TEXT PRIMARY KEY,
                conversation_history TEXT,
                timestamp TEXT,
                context_window TEXT
            )
            """
        )
        conn.commit()


def user_exists(user_id):
    """Check if a user exists in the table."""
    with sqlite3.connect(local_response_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM user_data WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

def add_user(user_id, context_window="You're a helpful AI assistant"):
    """Insert a new user entry if it doesn't already exist."""
    with sqlite3.connect(local_response_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO user_data (user_id, conversation_history, timestamp, context_window)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, json.dumps({}), datetime.now().isoformat(), context_window),
        )
        conn.commit()


def fetch_user_data(user_id):
    """Fetch data for a given user_id."""
    with sqlite3.connect(local_response_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_data WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return {
                "user_id": result[0],
                "conversation_history": json.loads(result[1]),
                "timestamp": result[2],
                "context_window": result[3],
            }
        return None


def update_conversation(user_id, question, answer, turn=3):
    """Update the conversation history for a given user_id and update the context window."""
    with sqlite3.connect(local_response_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT conversation_history FROM user_data WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            conversation_history = json.loads(result[0])
            new_index = max(
                map(int, conversation_history.keys()), default=0) + 1
            conversation_history[new_index] = f"Q: {question} | A: {answer}"

            sorted_history = [conversation_history[key]
                              for key in sorted(conversation_history.keys())]
            context_window = " ".join(sorted_history[-turn:])

            cursor.execute(
                """
                UPDATE user_data
                SET conversation_history = ?, timestamp = ?, context_window = ?
                WHERE user_id = ?
                """,
                (json.dumps(conversation_history),
                 datetime.now().isoformat(), context_window, user_id),
            )
            conn.commit()
