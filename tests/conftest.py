import pytest
import sqlite3
import os
import src.db as db

DB_PATH = os.getenv("SQLITE_PATH", "./datas/semantic_memory.db")

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    db.initialize_db()
    db.initialize_settings()

@pytest.fixture(autouse=True)
def clear_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM talk_logs;")
    conn.commit()
    conn.close()
