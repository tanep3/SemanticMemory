# 📘 SemanticMemory 要件定義書・設計書 (Rev. 2.1)

**Version 2.0.0 "Neural Dive"**

---

## 🌿 1. プロジェクト概要

### 🟢 名称

**SemanticMemory**

### 🟢 概要

自然言語テキスト（会話履歴やメモ等）を統合管理し、可視化・操作するためのシステム。
Version 2.0.0 では、既存のAPIサーバーに加え、ユーザーが記憶を直接管理できる **Web UI (Neural Dive)** を提供する。

* **Core**: 全文検索、意味検索、要約、ID管理を行うFastAPIサーバー
* **UI**: 記憶の閲覧、検索、編集、削除を行うWebダッシュボード

---

## 🌱 2. システム構成

* **言語**: Python
* **フレームワーク**: FastAPI
* **DB**
  * SQLite (全文検索・メタ管理)
  * ChromaDB (意味検索ベクトル)
* **Embeddingモデル**: SentenceTransformer (SBERT)
  * デフォルト: `cl-nagoya/ruri-small-v2`
* **要約モデル**: Ollama
  * デフォルト: `hf.co/SakanaAI/TinySwallow-1.5B-Instruct-GGUF:Q8_0`
* **Frontend (New)**
  * HTML5 / CSS3 (Modern Dark Theme) / Vanilla JS
  * FastAPIのStaticFilesとして配信

### 🟢 エンドポイント一覧

| URL | 説明 |
|---|---|
| `http://localhost:6001/` | **Neural Dive UI** (Web管理画面) |
| `http://localhost:6001/docs` | Swagger UI (API仕様) |
| `http://localhost:6001/api/*` | REST API |


---

## 🧠 3. 機能要件 (Backend / API)

### 🟢 主要API (既存)

| Endpoint | Method | 概要 |
|---|---|---|
| `/api/retrieve` | POST | 時系列＋意味検索のハイブリッド取得 |
| `/api/save` | POST | 会話ログの保存（SQLite + Chroma） |
| `/api/get_recent_db` | GET | 最新の記憶を取得 |
| `/api/search_db` | GET | キーワード全文検索 |
| `/api/search_vector` | POST | ベクトル意味検索 |
| `/api/delete_data_db` | DELETE | SQLiteからデータ削除 |
| `/api/delete_data_vector` | DELETE | Chromaからデータ削除 |
| `/api/summarize` | POST | テキストの要約生成 |

### 🆕 新規・改修API (v2.0.0)

| Endpoint | Method | 概要 |
|---|---|---|
| `/api/update_memory` | PATCH | **[NEW]** SQLite + Chroma 統合更新。`main_text`変更時はVector再埋め込み＋サマリー自動再生成。 |
| `/api/delete_memory` | DELETE | **[NEW]** SQLite + Chroma 同期一括削除 + audit_logs記録。 |
| `/api/cleanup_audit_logs` | POST | **[NEW]** audit_logsの古いレコードを削除。`max_age_days`指定可能（省略時は全削除）。 |
| `/api/get_recent_db` | GET | **[MODIFIED]** `offset` パラメータを追加し、ページネーション対応。 |
| `/api/mcp/recall_memory` | POST | **[NEW]** Vector検索 → SQLite生データ取得（MCPツール）。 |
| `/api/mcp/delete_memory` | POST | **[NEW]** HITL確認付き削除（MCPツール）。 |

---

## 🖥️ 4. 機能要件 (Frontend / UI)

**名称: Neural Dive Dashboard**

### 🟢 1. ユーザー認証
* **Basic認証**:
  * `.env` に `UI_USER`, `UI_PASS` が設定されている場合のみ有効化。
  * 設定がない場合は認証なしでアクセス可能（ローカル開発用）。

### 🟢 2. ダッシュボード (一覧表示)
* **カード表示**: 記憶をカード形式で時系列（新しい順）に表示。
* **ページネーション**: 「もっと読み込む」ボタン or 無限スクロールで追加データをロード (`offset` パラメータ使用)。
* **表示項目**:
  * 要約 (Summary)
  * 日時 (Timestamp)
  * 本文の抜粋 (Snippet)
  * ID

### 🟢 3. 検索 (Search)
* **2モード検索**:
  * テキスト入力欄を1つ設置。
  * **「キーワード検索」ボタン**: 全文検索 (`/api/search_db`)
  * **「意味検索」ボタン**: ベクトル検索 (`/api/search_vector`)
  * ユーザーが押したボタンに応じてどちらか一方を実行。

### 🟢 4. 詳細・編集 (Detail & Edit)
* **詳細モーダル**: カードクリックで詳細を表示。
  * `main_text` (会話全文)
  * `sub_text` (AI回答)
  * `summary_text` (要約)
* **編集機能**:
  * 上記フィールドを直接編集可能。
  * **保存ボタン**:
    * `main_text` が変更された場合 → Vector再埋め込み + サマリー自動再生成。
    * `sub_text` のみ変更 → DB更新のみ（Vector/サマリーは影響なし）。
    * `summary_text` のみ変更 → DB更新のみ（Vectorは `main_text` ベースなので影響なし）。
  * **サマリー再生成ボタン**:
    * 既存のサマリーが気に入らない場合、手動で再生成を要求。
    * 再生成結果は**プレビュー表示**され、ユーザーが確認・承認後に保存される。

### 🟢 5. 削除 (Delete)
* **個別削除**: カード上のゴミ箱アイコンから削除。
  * 削除前に確認ダイアログを表示。
  * `/api/delete_memory` を使用し、SQLiteとChromaの両方から削除。
  * 削除されたデータは `audit_logs` に記録される。

### 🟢 6. マイグレーション (Cleanup)
* **マイグレーションボタン**: 管理エリアに設置。
  * `audit_logs` の全レコードを物理削除。
  * 削除前に確認ダイアログを表示。
* **起動時自動クリーンアップ**:
  * アプリ起動時に1年（365日）以上経過した `audit_logs` を自動削除。

---

## 🎨 5. UIデザイン要件

### 🟢 コンセプト: "Neural Dive"
* **テーマ**: Deep Dark Mode
* **アクセント**: Neon Cyan / Purple
* **スタイル**: Glassmorphism, Floating Cards
* **UX**: 没入感があり、かつレスポンシブで高速な操作性。

---

## 📂 6. データ設計 (Backend)

### 🗃️ SQLite tables
* `talk_logs` (`id`, `main_text`, `sub_text`, `summary_text`, `create_time`, `update_time`)
* `embedding_links`
* `settings`
* `audit_logs` **[NEW]** (`id`, `action`, `target_id`, `deleted_data`, `timestamp`, `user_agent`)

---

## 🛡️ 7. セキュリティ

* **API**: 認証なし（ローカルネットワーク内利用を想定）
* **UI**: Basic認証 (Optional via .env: `UI_USER`, `UI_PASS`)
  * インターネット公開時はリバースプロキシ等でのSSL化と追加認証を強く推奨。

---

## 🚀 8. 改訂履歴

| Version | 内容 |
|---|---|
| v1.0.0 | Backend API Initial Release |
| v1.1.0 | OpenWebUI Filter Integration |
| v2.0.0 | "Neural Dive" UI Update (Dashboard, Search, Edit, Delete, Unified API) |

