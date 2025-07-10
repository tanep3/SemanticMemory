# 📘 SemanticMemory API仕様書（最終FIX版）

---

## 🌿 1. 命名規則

✅ **接頭辞（アクション）**

| 接頭辞           | 機能    |
| ------------- | ----- |
| `add`         | 新規登録  |
| `get_recent`  | 時系列取得 |
| `search`      | 検索    |
| `delete_data` | 削除    |
| `update`      | 更新    |
| `rebuild`     | 全再構築  |

---

✅ **末尾（ストレージ種別）**

| 末尾        | 対象                 |
| --------- | ------------------ |
| `_db`     | リレーショナルDB (SQLite) |
| `_vector` | ベクトルDB (Chroma)    |

---

✅ **複合API**

| 名称         | 機能        |
| ---------- | --------- |
| `save`     | 両DB同時登録   |
| `retrieve` | 両DBから併合取得 |

---

---

## 🟢 2. 単機能API

---

### 📗 2.1 データ新規登録 (SQLite)

#### `POST /add_db`

**概要**
主・副テキストをDBに保存。

**Body**

```json
{
  "main_text": "メインテキスト",
  "sub_text": "サブテキスト(任意)"
}
```

**レスポンス**

```json
{
  "status": "saved",
  "id": 123
}
```

---

---

### 📗 2.2 データ新規登録 (ベクトルDB)

#### `POST /add_vector`

**概要**
テキストをベクトルDBに埋め込み登録。

**Body**

```json
{
  "id": 123,
  "text": "埋め込みテキスト"
}
```

**レスポンス**

```json
{
  "status": "vector_saved",
  "id": "123"
}
```

---

---

### 📗 2.3 時系列取得 (SQLite)

#### `GET /get_recent_db`

**パラメータ**

* `limit` (int): 件数

**レスポンス**

```json
[
  {
    "id": 123,
    "main_text": "...",
    "sub_text": "...",
    "summary_text": "...",
    "create_time": "...",
    "update_time": "..."
  }
]
```

---

---

### 📗 2.4 全文検索 (SQLite)

#### `GET /search_db`

**パラメータ**

* `q` (string): キーワード
* `order` (`asc`/`desc`)
* `limit` (int)

**レスポンス**
(上と同じ)

---

---

### 📗 2.5 意味検索 (ベクトルDB)

#### `POST /search_vector`

**Body**

```json
{
  "query": "クエリテキスト",
  "threshold": 0.6,
  "limit": 5
}
```

**レスポンス**

```json
[
  {
    "id": "123",
    "text": "一致テキスト",
    "score": 0.88
  }
]
```

---

---

### 📗 2.6 データ削除 (SQLite)

#### `DELETE /delete_data_db`

**Body**

```json
{
  "id": 123
}
```

**レスポンス**

```json
{
  "status": "deleted",
  "id": 123
}
```

---

---

### 📗 2.7 データ削除 (ベクトルDB)

#### `DELETE /delete_data_vector`

**Body**

```json
{
  "id": "123"
}
```

**レスポンス**

```json
{
  "status": "vector_deleted",
  "id": "123"
}
```

---

---

### 📗 2.8 データ編集 (SQLite)

#### `PATCH /update_db`

**Body**

```json
{
  "id": 123,
  "main_text": "修正テキスト(任意)",
  "sub_text": "修正テキスト(任意)",
  "summary_text": "修正要約(任意)"
}
```

**レスポンス**

```json
{
  "status": "updated",
  "id": 123
}
```

---

---

### 📗 2.9 データ編集 (ベクトルDB)

#### `POST /update_vector`

**概要**
削除＋再埋め込み

**Body**

```json
{
  "id": "123",
  "text": "新しいテキスト",
  "regenerate_summary": true
}
```

**レスポンス**

```json
{
  "status": "vector_updated",
  "id": "123"
}
```

---

---

### 📗 2.10 再構築 (ベクトルDB)

#### `POST /rebuild_vector`

**概要**
全再埋め込み

**Body**

```json
{
  "sbert_model": "新モデル名",
  "regenerate_summary": true
}
```

**レスポンス**

```json
{
  "status": "rebuild_started"
}
```

---

---

### 📗 2.11 Ollama要約

#### `POST /summarize`

**Body**

```json
{
  "text": "要約するテキスト",
  "llm_model": "任意指定(オプション)"
}
```

**レスポンス**

```json
{
  "summary": "要約結果"
}
```

---

---

## 🟢 3. 複合機能API

---

### 📘 3.1 データ同時保存

#### `POST /save`

**概要**
SQLiteとベクトルDBに同時保存。

**Body**

```json
{
  "main_text": "メインテキスト",
  "sub_text": "サブテキスト(任意)",
  "summarize": true
}
```

**レスポンス**

```json
{
  "status": "saved",
  "id": 123
}
```

---

---

### 📘 3.2 データ併合取得

#### `POST /retrieve`

**Body**

```json
{
  "query": "意味検索クエリ",
  "threshold": 0.6,
  "limit": 5,
  "recent_limit": 5
}
```

**レスポンス**

```json
{
  "semantic": [
    {"id":"...", "text":"...", "score":0.9}
  ],
  "recent": [
    {"id": "...", "main_text":"...", "sub_text":"..."}
  ]
}
```

---

---

## 🟢 4. 設定管理API

---

### 📗 4.1 設定取得

#### `GET /settings`

**レスポンス**

```json
{
  "sbert_model": "...",
  "llm_model": "...",
  "cosine_threshold": "...",
  "recall_limit": "..."
}
```

---

---

### 📗 4.2 設定更新

#### `POST /settings`

**Body**

```json
{
  "key": "sbert_model",
  "value": "新モデル名"
}
```

**レスポンス**

```json
{
  "status": "updated",
  "key": "sbert_model"
}
```

---

---

## 📝 5. 注意事項

* IDは**SQLite・ベクトルDB共通**
* APIは将来拡張（タグ管理、複数モデル同時運用）
* 認証は未実装（自己利用前提）
* `rebuild_vector`は長時間処理

