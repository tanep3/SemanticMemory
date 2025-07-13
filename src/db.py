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
    "sbert_model": os.getenv("SBERT_MODEL", "cl-nagoya/ruri-small-v2"),
    "cosine_threshold": os.getenv("COSINE_THRESHOLD", "0.5"),
    "recall_limit": os.getenv("RECALL_LIMIT", "10"),
    "llm_model": os.getenv("LLM_MODEL", "hf.co/SakanaAI/TinySwallow-1.5B-Instruct-GGUF:Q8_0"),
    "auto_summarize": "true",
    "store_summary_in_vector": "true",
    "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
    "system_prompt": os.getenv("SYSTEM_PROMPT", "以下のテキストを日本語で簡潔に要約してください。")
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

from datetime import datetime, timezone

def update_talk_log(id_, main_text=None, sub_text=None, summary_text=None):
    """
    トークログを更新する。
    更新対象が1つもない場合は例外を投げる。
    """
    now = datetime.now(timezone.utc).isoformat()

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

    # 更新対象が1つもない場合
    if not fields:
        raise ValueError("At least one field must be provided for update.")

    # update_timeは必ず更新
    fields.append("update_time = ?")
    values.append(now)

    # WHERE句用のID
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

def get_recent_talk_logs(limit=None, order="create"):
    """
    最近のトークログを取得する。
    
    Args:
        limit (int, optional): 最大取得件数。
        order (str): 並べ替えのキー。'create' または 'update'。

    Returns:
        List[dict]: トークログのリスト。
    """
    if order not in ("create", "update"):
        raise ValueError("order must be 'create' or 'update'")    
    if order == "update":
        order_field = "update_time"
    else:
        order_field = "create_time"

    with get_conn() as conn:
        c = conn.cursor()
        sql = f"SELECT * FROM talk_logs ORDER BY {order_field} DESC"
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
