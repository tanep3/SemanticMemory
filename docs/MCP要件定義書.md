# 📘 SemanticMemory MCP 要件定義書・ツール仕様書

**v2.1.0 - stdio ラッパー方式**

---

## 1. 概要

### 目的
SemanticMemoryの常時プロセス（Auto Filter）を補完し、**必要なときだけ明示的に記憶を操作する**ためのMCPツールセットを提供する。

### アーキテクチャ
- **MCP**: `mcp/semantic_memory.py`（stdioラッパー）
- **API**: SemanticMemory REST API (`/api/mcp/*`)
- **クライアント**: mcpo、Claude Desktop、VS Code等

```
┌──────────────────────────────────────────────────────────┐
│                      mcpo コンテナ                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │ /app/.venv/bin/python                            │   │
│  │   /app/tools/semantic_memory.py                  │   │
│  │          ↓ (stdio JSON-RPC)                      │   │
│  └──────────────────────────────────────────────────┘   │
│              │                                           │
└──────────────│───────────────────────────────────────────┘
               │ HTTP (host.docker.internal:6001)
               ▼
┌──────────────────────────────────────────────────────────┐
│  SemanticMemory API                                      │
│  POST /api/mcp/recall_memory                             │
│  POST /api/mcp/delete_memory                             │
└──────────────────────────────────────────────────────────┘
```

---

## 2. mcpo 設定

### docker-compose.yml でのマウント

```yaml
services:
  openwebui-mcpo:
    image: ghcr.io/open-webui/mcpo:main
    volumes:
      - ./tools:/app/tools
```

### config.json

```json
{
  "mcpServers": {
    "semantic-memory": {
      "type": "stdio",
      "command": "/app/.venv/bin/python",
      "args": ["/app/tools/semantic_memory.py"],
      "env": {
        "SEMANTIC_API": "http://host.docker.internal:6001/api"
      }
    }
  }
}
```

---

## 3. MCPツール仕様

### 3.1 `recall_memory` - 明示的リコール

**目的**: 要約ではなく、元の記憶（生データ）をそのまま思い出す。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| query | string | (必須) | 検索クエリ |
| limit | integer | 3 | 取得件数 |
| threshold | number | 0.7 | コサイン類似度の閾値 |

### 3.2 `delete_memory` - 記憶削除（HITL対応）

**目的**: 不要な記憶を安全に削除する。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| id | integer | (必須) | 削除対象の記憶ID |
| confirm | boolean | false | 削除確認フラグ |

---

## 4. 重複排除 (Deduplication)

`ai_mcp_sample.py` では、`recall_memory` を使用した会話は**自動保存の対象外**となります。

| 条件 | 保存動作 |
|---|---|
| 通常の会話 | ✅ 自動保存 |
| `recall_memory` を使用した会話 | ❌ スキップ |

**理由**: `recall_memory` で呼び出した内容をLLMが説明すると、その応答は「既存の記憶」の言い換えになります。これを保存すると実質的に重複データとなるため、保存をスキップします。

---

## 5. 安全設計

| 操作 | 自動実行可否 | 理由 |
|---|---|---|
| `recall_memory` | ✅ 自動 | 読み取り専用 |
| `delete_memory` | ❌ HITL必須 | 破壊的操作 |

---

## 6. 改訂履歴

| Version | 内容 |
|---|---|
| v1.0-1.4 | 初回〜mcpo構成対応 |
| v2.0.0 | stdioラッパー方式に変更。SemanticMemory本体はREST APIのみ提供。 |
| **v2.1.0** | **重複排除機能を追加。recall_memory使用時の会話は自動保存をスキップ。** |
