# クライアント実装例 (Examples)

このディレクトリには、SemanticMemory APIを利用する具体的なクライアント実装例が含まれています。

## 1. Pythonクライアント・サンプル (`ai_sample.py`)

SemanticMemoryをRAG（検索拡張生成）として利用する、シンプルなPythonスクリプトです。
CLI（コマンドライン）上でAIと会話ができ、会話内容は自動的にSemanticMemoryに保存・検索されます。

### 特徴
- **会話の記憶**: ユーザーの発言とAIの応答をペアで保存します。
- **文脈の注入**: ユーザーの入力に関連する過去の記憶（Semantic Search）と、直近の会話履歴（Recent Logs）を自動的に取得し、システムプロンプトに組み込みます。
- **ストリーミング**: AIの応答をリアルタイムに表示します。

### 前提条件
- **SemanticMemory** が起動していること（デフォルト: `http://localhost:6001`）
- **Ollama** が起動していること（デフォルト: `http://localhost:11434`）
- Pythonライブラリのインストール:
  ```bash
  pip install requests ollama
  ```

### 使い方
`examples` ディレクトリ内で以下を実行します。

```bash
python ai_sample.py "質問内容"
```

---

## 2. MCP統合クライアント (`ai_mcp_sample.py`) [v2.0.0]

ai_sample.py の機能に加え、**MCP（Model Context Protocol）** ツールを使った明示的な記憶操作が可能なハイブリッドクライアントです。

### 特徴
- **自動記憶機能**: ai_sample.py と同等の自動取得・保存
- **recall_memory**: 「はっきり思い出して」で過去の生データを明示的に取得
- **delete_memory**: 「削除して」でHITL（Human-in-the-Loop）確認付き削除
- **エージェントループ**: LLMが複数回tool_callsを行う対話フロー

### 前提条件
- SemanticMemory API が起動していること（デフォルト: `http://localhost:6001`）
- Ollama が起動していること（デフォルト: `http://localhost:11434`）

### 使い方
```bash
# 対話モード
python ai_mcp_sample.py

# ワンショットモード
python ai_mcp_sample.py "たねちゃんについて思い出して"
```

---

## 3. MCPサーバー設定 [v2.0.0]

SemanticMemoryは `mcp/semantic_memory.py` で stdio MCP サーバーを提供します。

---

### 3.1 mcpo (OpenWebUI) での設定

**1. docker-compose.yml でマウント（mcpoのtoolsディレクトリにコピー）:**
```bash
cp /path/to/SemanticMemory/mcp/semantic_memory.py /path/to/mcpo/tools/
```

**2. config.json:**
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

**3. mcpoを再起動:**
```bash
docker restart openwebui-mcpo
```

---

### 3.2 Claude Desktop での設定

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "semantic-memory": {
      "command": "python",
      "args": ["/path/to/SemanticMemory/mcp/semantic_memory.py"],
      "env": {
        "SEMANTIC_API": "http://localhost:6001/api"
      }
    }
  }
}
```

---

### 3.3 VS Code / Cursor での設定

`.vscode/mcp.json`:

```json
{
  "servers": {
    "semantic-memory": {
      "command": "python",
      "args": ["/path/to/SemanticMemory/mcp/semantic_memory.py"],
      "env": {
        "SEMANTIC_API": "http://localhost:6001/api"
      }
    }
  }
}
```

---

### 3.4 提供されるMCPツール

| ツール名 | 説明 |
|---|---|
| `recall_memory` | Vector検索 → SQLite生データ取得。「はっきり思い出して」で使用。 |
| `delete_memory` | HITL確認付き削除。`confirm=false`で確認、`confirm=true`で実行。 |

> **📝 重複排除機能**
> `recall_memory` を使った会話は自動保存の対象外となります。これは「既存の記憶を参照しただけ」の会話が重複して保存されるのを防ぐためです。

---

### 3.5 OpenWebUI でのシステムプロンプト設定

OpenWebUIでMCPツールを正しく動作させるには、チャットのシステムプロンプトに以下を設定してください：

```
あなたは記憶管理機能を持つ親切なAIアシスタントです。

### あなたが使えるツール
- recall_memory: ユーザーが「はっきり思い出して」「詳しく教えて」と言った時、過去の記憶の生データを取得
- delete_memory: ユーザーが「この記憶を消して」と言った時、IDを指定して記憶を削除（確認必須）
```

> **💡 設定場所**
> OpenWebUI の **Workspace > Models > (使用するモデル) > System Prompt** で設定できます。

---

## 4. OpenWebUI フィルター (`open_webui_filter.py`)

[OpenWebUI](https://github.com/open-webui/open-webui) の **Functions (Filters)** 機能を使って、SemanticMemoryを統合するためのスクリプトです。
これを導入すると、OpenWebUI上のチャットで透過的に長期記憶を利用できるようになります。

### 特徴
- **自動記憶検索 (Retrieve)**: ユーザーが発言する前に、関連する過去の記憶をSemanticMemoryから検索し、コンテキスト（システムプロンプト）に注入します。
- **重複排除**: OpenWebUIが管理する「現在のスレッド履歴」との重複を防ぐため、SemanticMemoryからは「意味検索（Semantic Search）」の結果のみを取得します。
- **自動保存 (Save)**: AIの応答が完了すると、その会話ペア（User + AI）をSemanticMemoryにバックグラウンドで保存します。

### 導入手順
1. **OpenWebUI** をブラウザで開きます。
2. 右上のアイコンなどから **Admin Panel (管理者パネル)** > **Functions** に移動します。
3. **「+」ボタン** をクリックして新規作成します。
4. 名前（例: `SemanticMemory Connector`）を入力し、`open_webui_filter.py` の中身をエディタに貼り付けます。
5. **Save** して保存します。
6. Functions一覧画面で、作成したFunctionのトグルスイッチを **ON** にします。

### 設定 (Valves)
Functionを有効化すると、歯車アイコン（Settings）から以下の項目を設定できます。

- **api_url**: SemanticMemory APIのURL
    - OpenWebUIがDockerで動いている場合: `http://host.docker.internal:6001/api`
- **search_limit**: 検索する過去の記憶の数（デフォルト: `10`）
- **threshold**: ベクトル検索の類似度しきい値（デフォルト: `0.6`）
- **auto_save**: 会話の自動保存を有効にするか（デフォルト: `True`）
