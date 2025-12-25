#!/usr/bin/env python3
"""
semantic_memory.py - SemanticMemory MCP Server (stdio transport)

mcpoから実行されるstdio MCPサーバー。
SemanticMemory APIを呼び出してMCPツールを提供する。

【mcpo config.json への登録】
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

【セットアップ】
mcpoのtoolsディレクトリにこのファイルをコピー:
cp /path/to/SemanticMemory/mcp/semantic_memory.py /path/to/mcpo/tools/
"""

import os
import sys
import json
import urllib.request
import urllib.error

# 環境変数（Dockerのhost.docker.internalでホストにアクセス）
SEMANTIC_API = os.environ.get("SEMANTIC_API", "http://host.docker.internal:6001/api")


def log(msg: str):
    """stderrにログ出力（stdoutはJSON-RPCで使用）"""
    sys.stderr.write(f"[semantic_memory] {msg}\n")
    sys.stderr.flush()


def call_api(endpoint: str, payload: dict) -> dict:
    """SemanticMemory APIを呼び出す（requestsなしで動作）"""
    try:
        url = f"{SEMANTIC_API}/{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"status": "error", "message": f"Connection error: {e.reason}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def handle_initialize(params: dict) -> dict:
    """MCP初期化"""
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "semantic-memory",
            "version": "2.0.0"
        },
        "capabilities": {
            "tools": {}
        }
    }


def handle_list_tools(params: dict) -> dict:
    """利用可能なツール一覧"""
    return {
        "tools": [
            {
                "name": "recall_memory",
                "description": "過去の記憶を明示的に思い出す。要約ではなく元の会話ログ（生データ）を取得する。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "検索クエリ（例: たねちゃん、プロジェクトの決定事項）"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "取得件数",
                            "default": 3
                        },
                        "threshold": {
                            "type": "number",
                            "description": "コサイン類似度の閾値",
                            "default": 0.7
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "delete_memory",
                "description": "不要な記憶を削除する。削除前に必ずユーザーの確認が必要。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "削除対象の記憶ID"
                        },
                        "confirm": {
                            "type": "boolean",
                            "description": "削除確認フラグ（trueで実行）",
                            "default": False
                        }
                    },
                    "required": ["id"]
                }
            }
        ]
    }


def handle_call_tool(params: dict) -> dict:
    """ツール実行"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if tool_name == "recall_memory":
        result = call_api("mcp/recall_memory", {
            "query": arguments.get("query", ""),
            "limit": arguments.get("limit", 3),
            "threshold": arguments.get("threshold", 0.7)
        })
    elif tool_name == "delete_memory":
        result = call_api("mcp/delete_memory", {
            "id": arguments.get("id"),
            "confirm": arguments.get("confirm", False)
        })
    else:
        result = {"status": "error", "message": f"Unknown tool: {tool_name}"}

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2)
            }
        ]
    }


def process_request(request: dict) -> dict:
    """リクエストを処理"""
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    handlers = {
        "initialize": handle_initialize,
        "tools/list": handle_list_tools,
        "tools/call": handle_call_tool,
    }

    handler = handlers.get(method)
    if handler:
        result = handler(params)
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    else:
        # 未対応メソッドは空レスポンス（notifications等）
        if req_id is not None:
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        return None  # notificationには応答しない


def main():
    """stdio JSON-RPCメインループ"""
    log(f"Starting SemanticMemory MCP Server (API: {SEMANTIC_API})")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = process_request(request)
            if response:
                print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            log(f"JSON parse error: {e}")
        except Exception as e:
            log(f"Error: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
