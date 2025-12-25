[🇬🇧 English](./README.md)

---

# SemanticMemory

汎用的な会話履歴・メモの保存と、ベクトル検索APIを提供するFastAPIアプリケーションです。

## 🌟 Features

- **会話ログの保存・更新・削除**: SQLite + ChromaDB によるデュアルストレージ
- **ベクトル検索**: SBERTによる埋め込み生成とセマンティック検索
- **自動要約**: Ollamaによる要約生成
- **Neural Dive UI**: ブラウザから記憶を管理できるWebインターフェース
- **MCP統合**: MCPプロトコルによるAIツール連携
- **RESTful API**: FastAPIによる高速なAPIサーバー
- **Docker対応**: かんたんデプロイ

---

## 🚀 Getting Started

### 1. Dockerで起動

```bash
docker compose up -d
```

デフォルトで以下の設定が使われます：

* `./datas` ディレクトリに SQLite / ChromaDB データ
* ポート: `6001`

### 2. APIドキュメント

```
http://localhost:6001/docs
```

FastAPIのSwagger UIでAPIドキュメントを確認できます。

---

## 🧠 Neural Dive UI（管理画面）

ブラウザから記憶を閲覧・編集・削除できる管理画面です。

### アクセス

```
http://localhost:6001/
```

### 機能

| 機能 | 説明 |
|---|---|
| 📋 **記憶一覧** | 保存された会話ログを時系列またはキーワードで検索 |
| ✏️ **編集** | main_text, sub_text, summary を個別に編集（main_text変更時は自動でサマリー再生成） |
| 🗑️ **削除** | 不要な記憶を削除 |
| 🔍 **孤児ベクトル検出** | SQLiteとChromaDBの不整合を検出して修復 |

### 認証（オプション）

`.env` で Basic認証を設定できます：

```env
UI_USER=admin
UI_PASS=secret
```

---

## 🔗 MCP統合（AIツール連携）

MCP（Model Context Protocol）を使って、AIアシスタントから記憶を操作できます。

### 提供ツール

| ツール | 説明 |
|---|---|
| `recall_memory` | 過去の記憶を明示的に検索・取得 |
| `delete_memory` | 記憶を削除（確認付き） |

### 設定方法

詳細は以下を参照してください：
- [examples/usage.md](examples/usage.md) - クライアント実装例・MCP設定
- [docs/MCP要件定義書.md](docs/MCP要件定義書.md) - MCP仕様

---

## 📁 クライアント実装例

| ファイル | 説明 |
|---|---|
| `examples/ai_sample.py` | 基本的なRAGクライアント |
| `examples/ai_mcp_sample.py` | MCP統合クライアント（HITL対応） |
| `examples/open_webui_filter.py` | OpenWebUI用フィルター |

詳細は [examples/usage.md](examples/usage.md) を参照してください。

---

## ⚙️ 環境変数

`.env` または `docker-compose.yml` で設定：

| 変数 | デフォルト | 説明 |
|---|---|---|
| `SQLITE_PATH` | `./datas/semantic_memory.db` | SQLiteファイルパス |
| `CHROMA_PATH` | `./datas/chroma/` | ChromaDBディレクトリ |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |
| `SBERT_MODEL` | `cl-nagoya/ruri-small-v2` | 埋め込みモデル |
| `UI_USER` / `UI_PASS` | (空) | UI認証（両方設定で有効） |
| `API_TIMEOUT` | `30` | クライアントAPIタイムアウト（秒） |

---

## 🔄 Update

```bash
./scripts/auto_update.sh
```

Git pull、Dockerビルド、古いイメージの削除を自動で行います。

---

## 📚 使用モデル・ライセンス

このプロジェクトでは以下の外部モデルを利用しています：

* [cl-nagoya/ruri-small-v2](https://huggingface.co/cl-nagoya/ruri-small-v2) - Apache 2.0, Gemma Terms
* [SakanaAI/TinySwallow-1.5B-Instruct-GGUF](https://huggingface.co/SakanaAI/TinySwallow-1.5B-Instruct-GGUF) - Apache 2.0, Gemma Terms

モデルライセンスは本リポジトリのライセンスとは異なります。利用者自身でライセンス内容を確認し、遵守してください。

---

## ⚖️ License

This project is licensed under the MIT License.
See [LICENSE](./LICENSE) for details.
