"""
title: SemanticMemory Filter
author: tane
version: 1.1
description: Integrates external SemanticMemory API for long-term memory (RAG).
"""

import requests
import json
from pydantic import BaseModel, Field
from typing import Optional

# ユーザーがOpenWebUIの設定画面で変更できる値
class Valves(BaseModel):
    # SemanticMemory APIのURL (Docker等の環境に合わせて変更してください)
    # OpenWebUIがDocker内、APIがホストなら http://host.docker.internal:6001/api など
    api_url: str = Field(default="http://host.docker.internal:6001/api", description="SemanticMemory API Base URL")
    
    # 検索設定
    search_limit: int = Field(default=10, description="Number of vector memories to retrieve")
    threshold: float = Field(default=0.6, description="Cosine similarity threshold for vector search")
    
    # 保存設定
    auto_save: bool = Field(default=True, description="Automatically save conversation to memory")

class Filter:
    def __init__(self):
        self.valves = Valves()

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        User Input -> [Filter: Retrieve Memory] -> LLM
        ユーザー入力前に記憶を検索し、システムプロンプトに注入する
        """
        messages = body.get("messages", [])
        if not messages:
            return body

        # 最後のユーザー発言を取得
        last_user_message = messages[-1]["content"]
        
        # 1. 記憶の検索 (Retrieve)
        print(f"SemanticMemory: Retrieving for '{last_user_message}'...")
        try:
            payload = {
                "query": last_user_message,
                "limit": self.valves.search_limit,
                "recent_limit": 0, # OpenWebUIが直近会話を保持するため、ここでは取得しない
                "threshold": self.valves.threshold
            }
            # APIコール
            response = requests.post(f"{self.valves.api_url}/retrieve", json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()

            # 2. コンテキスト構築
            memory_context = self._build_context(data)
            
            if memory_context:
                # 3. システムプロンプトへの注入
                # 既存のシステムプロンプトを探す
                system_message = next((m for m in messages if m["role"] == "system"), None)
                
                injection_text = f"\n\n### Semantic Memory (External RAG)\n{memory_context}\n"

                if system_message:
                    # 既存のシステムプロンプトに追記
                    system_message["content"] += injection_text
                else:
                    # システムプロンプトがない場合は先頭に追加
                    body["messages"].insert(0, {
                        "role": "system", 
                        "content": f"You are a helpful AI assistant.\n{injection_text}"
                    })
                
                print("SemanticMemory: Injected memories into context.")

        except Exception as e:
            print(f"SemanticMemory Error (Retrieve): {e}")
            # エラーでもチャットは止めない

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        LLM Output -> [Filter: Save Memory] -> User
        AIの応答完了後に、会話ログを保存する
        """
        if not self.valves.auto_save:
            return body

        messages = body.get("messages", [])
        if not messages:
            return body

        # OpenWebUIのoutletでは、body["messages"]に全履歴が入ってくる
        # 最後がAIの応答、その一つ前がユーザーの入力と仮定
        if len(messages) < 2:
            return body

        ai_message = messages[-1]["content"]
        user_message = messages[-2]["content"]

        # ストリーミング終了後などに空で来ることがあるのでガード
        if not ai_message or not user_message:
            return body

        # 保存処理
        print(f"SemanticMemory: Saving conversation...")
        try:
            # [user] [agent] 形式で保存
            entry_text = f"[user] {user_message}\n[agent] {ai_message}"
            
            payload = {
                "main_text": entry_text,
                "sub_text": ai_message, # 個別フィールドにも入れておく
                "summarize": True       # 要約をサーバーに任せる
            }
            
            # APIコール (非同期っぽく投げ捨てるのが理想だが、ここではシンプルに同期実行)
            # タイムアウトを短めにしてUXへの影響を抑える
            requests.post(f"{self.valves.api_url}/save", json=payload, timeout=3)
            print("SemanticMemory: Saved successfully.")

        except Exception as e:
            print(f"SemanticMemory Error (Save): {e}")
            
        return body

    def _build_context(self, data: dict) -> str:
        """APIレスポンスからプロンプト用テキストを作成"""
        context_lines = []
        
        # 意味検索（過去の記憶）
        semantic_logs = data.get("semantic", [])
        if semantic_logs:
            context_lines.append("#### Relevant Past Memories:")
            for log in semantic_logs:
                # document: テキスト, score: 類似度
                # scoreは参考程度に表示（または隠しても良い）
                context_lines.append(f"- {log['document']}")
            context_lines.append("")

        return "\n".join(context_lines)
