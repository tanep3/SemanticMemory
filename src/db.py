import sqlite3
import os
from datetime import datetime, timezone, UTC

DB_PATH = os.getenv("SQLITE_PATH", "./datas/semantic_memory.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

# テーブル作成
def initialize_db():
    with get_conn() as conn:
        c = conn.cursor()
        # talk_logs
        c.execute("""
        CREATE TABLE IF NOT EXISTS talk_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_text TEXT NOT NULL,
            sub_text TEXT,
            summary_text TEXT,
            create_time TEXT NOT NULL,
            update_time TEXT NOT NULL
        )
        """)
        # settings
        c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        conn.commit()

# 設定初期値
DEFAULT_SETTINGS = {
    "sbert_model": "cl-nagoya/ruri-small-v2",
    "cosine_threshold": "0.8",
    "recall_limit": "5",
    "llm_model": "hf.co/SakanaAI/TinySwallow-1.5B-Instruct-GGUF:Q8_0",
    "auto_summarize": "true",
    "store_summary_in_vector": "true",
    "ollama_url": "http://localhost:11434"
}

# settings初期化
def initialize_settings():
    with get_conn() as conn:
        c = conn.cursor()
        for k, v in DEFAULT_SETTINGS.items():
            c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()

# talk_logs操作
def insert_talk_log(main_text, sub_text=None, summary_text=None):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
        INSERT INTO talk_logs (main_text, sub_text, summary_text, create_time, update_time)
        VALUES (?, ?, ?, ?, ?)
        """, (main_text, sub_text, summary_text, now, now))
        conn.commit()
        return c.lastrowid

def update_talk_log(id_, main_text=None, sub_text=None, summary_text=None):
    now = datetime.now(UTC).isoformat()
    fields = []
    values = []
    if main_text is not None:
        fields.append("main_text = ?")
        values.append(main_text)
    if sub_text is not None:
        fields.append("sub_text = ?")
        values.append(sub_text)
    if summary_text is not None:
        fields.append("summary_text = ?")
        values.append(summary_text)
    fields.append("update_time = ?")
    values.append(now)
    values.append(id_)
    sql = f"UPDATE talk_logs SET {', '.join(fields)} WHERE id = ?"
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(sql, values)
        conn.commit()
        return c.rowcount

def delete_talk_log(id_):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM talk_logs WHERE id = ?", (id_,))
        conn.commit()
        return c.rowcount

def get_talk_log_by_id(id_):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM talk_logs WHERE id = ?", (id_,))
        row = c.fetchone()
        if row:
            return dict(zip([d[0] for d in c.description], row))
        return None

def get_recent_talk_logs(limit=None):
    with get_conn() as conn:
        c = conn.cursor()
        sql = "SELECT * FROM talk_logs ORDER BY create_time DESC"
        if limit:
            sql += f" LIMIT {limit}"
        c.execute(sql)
        rows = c.fetchall()
        return [dict(zip([d[0] for d in c.description], row)) for row in rows]

def search_talk_logs(keyword, order="desc", limit=None):
    with get_conn() as conn:
        c = conn.cursor()
        sql = f"""
        SELECT * FROM talk_logs
        WHERE main_text LIKE ?
        ORDER BY create_time {order.upper()}
        """
        if limit:
            sql += f" LIMIT {limit}"
        c.execute(sql, (f"%{keyword}%",))
        rows = c.fetchall()
        return [dict(zip([d[0] for d in c.description], row)) for row in rows]

# 設定操作
def get_settings():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM settings")
        rows = c.fetchall()
        return {k: v for k, v in rows}

def update_setting(key, value):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
        conn.commit()
        return c.rowcount

# テスト用truncate
def truncate_talk_logs():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM talk_logs")
        conn.commit()
