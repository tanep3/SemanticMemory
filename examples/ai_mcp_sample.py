#!/usr/bin/env python3
"""
ai_mcp_sample.py - MCP統合版AIクライアント（ハイブリッド）

【自動記憶機能】（ai_sample.py と同等）
- 会話開始時に関連記憶を自動取得してコンテキストに注入
- 会話終了後に自動保存

【MCP拡張機能】
- recall_memory: 明示的に生データを思い出す
- delete_memory: 不要な記憶を削除（HITL確認付き）

mcpo HTTP経由でMCPツールを呼び出し、Human-in-the-Loop (HITL) で
削除操作を安全に実行します。
"""

import sys
import json
import requests
import ollama
import os

# ===========================================
# 設定
# ===========================================
SEMANTIC_API = "http://localhost:6001/api"  # SemanticMemory API
MCPO_URL = "http://localhost:3300"  # mcpo エンドポイント
OLLAMA_MODEL = 'gemini-3-flash-preview:cloud'  # 環境に合わせて変更
MAX_ITERATIONS = 10  # エージェントループの最大反復回数
API_TIMEOUT = int(os.getenv("API_TIMEOUT", 30))  # APIタイムアウト（秒）

# ===========================================
# MCPツール定義（LLMに渡す形式）
# ===========================================
MCP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "過去の記憶を明示的に思い出す。要約ではなく、元の会話ログ（生データ）を取得する。ユーザーが「はっきり思い出して」「詳しく教えて」と言った時に使う。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "検索クエリ（例: たねちゃん、プロジェクトの決定事項）"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "取得件数（デフォルト: 3）",
                        "default": 3
                    },
                    "threshold": {
                        "type": "number",
                        "description": "コサイン類似度の閾値（デフォルト: 0.7）",
                        "default": 0.7
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": "不要な記憶を削除する。削除前に必ずユーザーの確認が必要。ユーザーが「この記憶を消して」「削除して」と言った時に使う。",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "削除対象の記憶ID"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "削除確認フラグ（初回はfalseで確認、承認後にtrueで実行）",
                        "default": False
                    }
                },
                "required": ["id"]
            }
        }
    }
]

# ===========================================
# 自動記憶機能（ai_sample.py由来）
# ===========================================
def retrieve_auto_context(query: str) -> tuple[str, str]:
    """
    自動的に関連記憶を取得してコンテキストを構築する。
    Returns: (vector_context, recent_context)
    """
    retrieve_payload = {
        "query": query,
        "limit": 5,
        "recent_limit": 5,
        "threshold": 0.5
    }

    try:
        response = requests.post(f"{SEMANTIC_API}/retrieve", json=retrieve_payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 時系列（最近の会話）
        recent_logs = data.get("recent", [])
        recent_context = ""
        if recent_logs:
            for log in reversed(recent_logs):
                recent_context += f"[user] {log['main_text']}\n"
                if log.get('sub_text'):
                    recent_context += f"[agent] {log['sub_text']}\n"
        else:
            recent_context = "(なし)"

        # 意味検索（関連する記憶）
        semantic_logs = data.get("semantic", [])
        vector_context = ""
        if semantic_logs:
            for log in semantic_logs:
                vector_context += f"- {log['document']} (Score: {log['score']:.2f})\n"
        else:
            vector_context = "(なし)"

        return vector_context, recent_context

    except Exception as e:
        print(f"[Auto-Retrieve Error] {e}")
        return "(Error)", "(Error)"


def save_conversation(question: str, response: str):
    """会話を自動保存する"""
    # ノイズフィルタ
    if len(response) < 10 or len(question) < 5:
        print("(Skipped saving: message too short)")
        return

    entry_text = f"[user] {question}\n[agent] {response}"

    # 重複チェック (Deduplication)
    # 既存の記憶と非常に似ている（95%以上）場合は保存をスキップする
    try:
        check_payload = {
            "query": entry_text,
            "limit": 1,
            "threshold": 0.95  # ほぼ完全一致のみ検知
        }
        res = requests.post(f"{SEMANTIC_API}/retrieve", json=check_payload, timeout=API_TIMEOUT)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                # resultsはscore降順で返る前提
                top_score = results[0].get("score", 0.0)
                if top_score >= 0.95:
                    print(f"(Skipped saving: Duplicate memory found, score={top_score:.4f})")
                    return
    except Exception as e:
        print(f"[Deduplication Check Failed] {e}")
        # チェック失敗時は保存処理を続行

    save_payload = {
        "main_text": entry_text,
        "sub_text": response,
        "summarize": True
    }

    try:
        # タイムアウトを環境変数で設定可能に（デフォルト: 30秒）
        res = requests.post(f"{SEMANTIC_API}/save", json=save_payload, timeout=API_TIMEOUT)
        if res.status_code == 200:
            print("(Memory saved)")
        else:
            print(f"(Save failed: {res.text})")
    except Exception as e:
        print(f"(Save error: {e})")


# ===========================================
# MCPツール呼び出し関数（SemanticMemory MCP API）
# ===========================================

def recall_memory(query: str, limit: int = 3, threshold: float = 0.7) -> dict:
    """記憶を明示的に思い出す"""
    try:
        response = requests.post(
            f"{SEMANTIC_API}/mcp/recall_memory",
            json={"query": query, "limit": limit, "threshold": threshold},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


def delete_memory_api(memory_id: int, confirm: bool = False) -> dict:
    """記憶を削除する（HITL必須）"""
    try:
        response = requests.post(
            f"{SEMANTIC_API}/mcp/delete_memory",
            json={"id": memory_id, "confirm": confirm},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


# ===========================================
# Human-in-the-Loop (HITL) 処理
# ===========================================
def handle_tool_call_with_hitl(tool_name: str, arguments: dict) -> str:
    """ツール呼び出しを処理。delete_memoryはHITL確認を実施。"""
    print(f"\n[Tool実行要求]")
    print(f"  ツール: {tool_name}")
    print(f"  引数: {json.dumps(arguments, ensure_ascii=False, indent=4)}")

    if tool_name == "delete_memory":
        if not arguments.get("confirm", False):
            preview = delete_memory_api(arguments["id"], confirm=False)

            if preview.get("status") == "confirmation_required":
                print(f"\n  [削除対象の記憶]")
                memory = preview.get("memory", {})
                print(f"    ID: {memory.get('id')}")
                print(f"    要約: {memory.get('summary_text', '(なし)')}")
                print(f"    本文: {memory.get('main_text', '(なし)')[:100]}...")

                try:
                    confirm = input("\n  この記憶を削除しますか？ [y/N]: ").strip().lower()
                except EOFError:
                    confirm = "n"

                if confirm in ("y", "yes"):
                    result = delete_memory_api(arguments["id"], confirm=True)
                    return json.dumps(result, ensure_ascii=False)
                else:
                    return json.dumps({"status": "cancelled", "message": "ユーザーにより削除がキャンセルされました"})
            else:
                return json.dumps(preview, ensure_ascii=False)
        else:
            # confirm=Trueで呼ばれた場合（通常はここには来ない）
            result = delete_memory_api(arguments["id"], confirm=True)
            return json.dumps(result, ensure_ascii=False)

    elif tool_name == "recall_memory":
        result = recall_memory(
            arguments.get("query", ""),
            arguments.get("limit", 3),
            arguments.get("threshold", 0.7)
        )
        return json.dumps(result, ensure_ascii=False)

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ===========================================
# エージェントループ（ハイブリッド）
# ===========================================
def agent_loop(user_input: str, auto_context: bool = True) -> str:
    """
    ハイブリッドエージェントループ。
    - 自動記憶機能でコンテキストを注入
    - MCPツールで明示的操作に対応
    - 会話を自動保存
    """
    # 1. 自動記憶取得（ai_sample.py機能）
    memory_section = ""
    recent_context = "(なし)"
    
    if auto_context:
        print("(Retrieving memories...)")
        vector_context, recent_context = retrieve_auto_context(user_input)
        
        if vector_context != "(なし)":
            memory_section = (
                "\n\n=== RELEVANT MEMORY FOR CONTEXT ===\n"
                "The following are past interactions related to the current topic. "
                "Use them to provide consistent and personalized responses.\n"
                f"{vector_context}\n"
                "====================================\n\n"
            )

    # 2. システムプロンプト構築
    system_prompt = f"""{memory_section}
あなたは記憶管理機能を持つ親切なAIアシスタントです。

### 直近の会話 (History)
{recent_context}

### あなたが使えるツール
- recall_memory: ユーザーが「はっきり思い出して」「詳しく教えて」と言った時、過去の記憶の生データを取得
- delete_memory: ユーザーが「この記憶を消して」と言った時、記憶を削除（確認必須）

### 制約
- 日本語で回答してください。
- 通常の会話では自動的に注入された記憶を参考にしてください。
- ツールは「明示的に思い出したい」「削除したい」時だけ使ってください。
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    final_response = ""
    iteration = 0
    recall_memory_used = False  # recall_memoryが使われたら保存をスキップ

    # 3. エージェントループ
    while iteration < MAX_ITERATIONS:
        iteration += 1

        # デバッグ: Ollamaに渡すメッセージを表示
        # print(f"\n[DEBUG] Ollama request - {len(messages)} messages")
        # print(json.dumps(messages, ensure_ascii=False, indent=2))
        
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=MCP_TOOLS,
                stream=False,
                options={"num_ctx": 128000}  # Gemini 3 Flash対応の大きなコンテキスト
            )
        except Exception as e:
            print(f"Ollama Error: {e}")
            break

        message = response.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", [])

        # アシスタントメッセージを履歴に追加
        # 【重要】Ollama/Geminiの方言問題を回避するため、tool_callsオブジェクトは履歴に残さず、
        # テキスト形式でツール実行を記録する "Manual Tool Loop" パターンを採用。
        # これにより 500 Internal Server Error を確実に回避できる。
        
        assistant_content = content
        if tool_calls:
            tool_names = [tc.get("function", {}).get("name", "unknown") for tc in tool_calls]
            if not assistant_content:
                assistant_content = f"(Activating tools: {', '.join(tool_names)}...)"
            else:
                assistant_content += f"\n(Activating tools: {', '.join(tool_names)}...)"

        messages.append({
            "role": "assistant",
            "content": assistant_content
            # tool_calls は意図的に含めない
        })

        # ループ終了条件: tool_callsがなければ終了
        if not tool_calls:
            if content:
                print(f"\nAssistant: {content}")
                final_response = content
            break

        # Tool Callを処理
        for idx, tc in enumerate(tool_calls):
            func = tc.get("function", {})
            tool_name = func.get("name")
            args = func.get("arguments", {})

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            # ツール実行（HITL含む）
            result = handle_tool_call_with_hitl(tool_name, args)
            print(f"  結果: {result[:200]}..." if len(result) > 200 else f"  結果: {result}")

            # recall_memoryが使われたらフラグを立てる
            if tool_name == "recall_memory":
                recall_memory_used = True

            # ツール結果を user メッセージとして返す（最も互換性が高い方法）
            messages.append({
                "role": "user",
                "content": f"【ツール {tool_name} の実行結果】\n{result}"
            })

    if iteration >= MAX_ITERATIONS:
        print("\n[警告] 最大ループ回数に達しました")

    # 4. 会話を自動保存（ai_sample.py機能）
    # recall_memoryを使った会話は「既存の記憶の参照」なので保存しない
    if recall_memory_used:
        print("(Skipped saving: Recall-based conversation)")
    elif final_response and auto_context:
        save_conversation(user_input, final_response)

    return final_response


# ===========================================
# メイン
# ===========================================
def main():
    print("=== SemanticMemory MCP Client (Hybrid) ===")
    print("通常の会話: 自動的に記憶を参照・保存します")
    print("明示的操作: 「はっきり思い出して」「削除して」で生データにアクセス")
    print("終了するには 'quit' と入力してください。\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except EOFError:
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        agent_loop(user_input)


if __name__ == "__main__":
    # コマンドライン引数がある場合はワンショット実行
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
        agent_loop(query)
    else:
        # 対話モード
        main()

