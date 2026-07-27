import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest


TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="semantic-memory-tests-"))
os.environ["SQLITE_PATH"] = str(TEST_DATA_DIR / "semantic_memory.db")
os.environ["CHROMA_PATH"] = str(TEST_DATA_DIR / "chroma")
os.environ["SBERT_DEVICE"] = "cpu"

import src.chroma as chroma
import src.db as db
import src.ollama as ollama

DB_PATH = os.environ["SQLITE_PATH"]

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    db.initialize_db()
    db.initialize_settings()
    chroma.clear_collection()
    yield
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)

@pytest.fixture(autouse=True)
def clear_db(monkeypatch):
    monkeypatch.setattr(
        ollama,
        "summarize_text",
        lambda text, **kwargs: f"要約: {text}",
    )
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM talk_logs;")
    conn.commit()
    conn.close()
    for key, value in db.DEFAULT_SETTINGS.items():
        db.update_setting(key, value)
    chroma.clear_collection()
