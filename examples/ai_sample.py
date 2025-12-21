#!/usr/bin/env python3

import sys
import json
import requests
import ollama

# SemanticMemory APIのURL
SEMANTIC_API = "http://localhost:6001/api"

if len(sys.argv) < 2:
    print("使用方法: ./ai_sample.py '質問内容'")
    sys.exit(1)

question = ' '.join(sys.argv[1:])
print(f"User: {question}\n")

# ----------------------------------------------------
# 1. 記憶の取得 (Retrieve)
# ----------------------------------------------------
print("Thinking... (Retrieving memories)")

# /retrieve エンドポイントを使うと、時系列＋意味検索を一括で取得できるので便利です！
retrieve_payload = {
    "query": question,
    "limit": 5,        # 意味検索（過去の記憶）件数
    "recent_limit": 5, # 直近の会話件数
    "threshold": 0.5   # 類似度閾値
}

try:
    response = requests.post(f"{SEMANTIC_API}/retrieve", json=retrieve_payload)
    response.raise_for_status()
    data = response.json()
    
    # 時系列（最近の会話）
    recent_logs = data.get("recent", [])
    recent_context = ""
    if recent_logs:
        # リストは新しい順に来るので、会話として成立させるために逆順（古い順）にするのがコツ
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
            # documentにはテキスト、scoreには類似度が入っています
            vector_context += f"- {log['document']} (Score: {log['score']:.2f})\n"
    else:
        vector_context = "(なし)"

except Exception as e:
    print(f"Error retrieving memories: {e}")
    recent_context = "(Error)"
    vector_context = "(Error)"


# ----------------------------------------------------
# 2. システムプロンプトの構築
# ----------------------------------------------------
system_prompt = f"""
あなたは親切なAIアシスタントです。以下の記憶を参考に回答してください。

### 過去の関連記憶 (Context)
{vector_context}

### 直近の会話 (History)
{recent_context}

### 制約
- 日本語で回答してください。
- 100文字程度で簡潔に答えてください。
"""

# ----------------------------------------------------
# 3. LLM生成 (Ollama Streaming)
# ----------------------------------------------------
print("Agent: ", end="", flush=True)

full_response = ""
try:
    stream = ollama.chat(
        model='gemini-3-flash-preview:cloud', # 環境に合わせて変更してください
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': question}
        ],
        stream=True
    )

    for chunk in stream:
        content = chunk['message']['content']
        print(content, end='', flush=True)
        full_response += content

except Exception as e:
    print(f"\nOllama Error: {e}")
    full_response = "(生成エラー)"

print("\n")

# ----------------------------------------------------
# 4. 記憶の保存 (Save)
# ----------------------------------------------------
# 会話を [user] ... [agent] ... というペアの形で保存するのがポイント
# main_textに会話全文、sub_textにAgentの回答、などを入れる運用もアリですが
# ここでは main_text にQ&Aセットを入れて、強力な文脈記憶にします。

print("(Saving memory...)")

entry_text = f"[user] {question}\n[agent] {full_response}"
save_payload = {
    "main_text": entry_text,
    "sub_text": full_response, # 念のため個別に持っておく（検索結果表示用などで便利）
    "summarize": True          # 要約も任せる
}

try:
    res = requests.post(f"{SEMANTIC_API}/save", json=save_payload)
    if res.status_code == 200:
        print("-> Saved successfully!")
    else:
        print(f"-> Save failed: {res.text}")
except Exception as e:
    print(f"-> Save error: {e}")
