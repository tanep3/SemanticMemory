# SemanticMemory

汎用的な会話履歴・メモの保存と、ベクトル検索APIを提供するFastAPIアプリケーションです。

## 🌟 Features

- 会話ログの保存、更新、削除
- SBERTによる埋め込み生成とベクトル検索
- Ollamaによる要約
- ChromaDBによるベクトルストレージ
- RESTful API
- Docker対応

## 🚀 Getting Started

### 1. Dockerで起動

```bash
docker compose up -d
````

デフォルトで以下の設定が使われます:

* `./datas` ディレクトリにChromaDBデータ
* `./logs` ディレクトリにログ
* ポート: `6001`(ホスト) → `8000`(コンテナ)

### 2. APIエンドポイント

アプリが起動したら以下にアクセスしてください:

```
http://localhost:6001/docs
```

FastAPIのSwagger UIでAPIドキュメントを確認できます。

### 3. 環境変数

Docker Composeで設定:

```yaml
environment:
  - SQLITE_PATH=/app/semantic_memory.db
  - CHROMA_PATH=/app/datas/chroma
  - OLLAMA_URL=http://localhost:11434
```

**環境変数を変更する場合:**

* `.env` ファイルを編集するか
* `docker-compose.yml` 内の `environment` を書き換えて再起動

---

## 📚 使用モデル・ライセンス

このプロジェクトでは以下の外部モデルを利用しています:

* [cl-nagoya/ruri-small-v2](https://huggingface.co/cl-nagoya/ruri-small-v2)

  * License: Apache 2.0, Gemma Terms & Prohibited Use
* [SakanaAI/TinySwallow-1.5B-Instruct-GGUF](https://huggingface.co/SakanaAI/TinySwallow-1.5B-Instruct-GGUF)

  * License: Apache 2.0, Gemma Terms & Prohibited Use
  * **商用利用の場合**: Qwen (Apache 2.0) と Gemmaライセンスの両方に準拠する必要があります。

モデルライセンスは本リポジトリのライセンスとは異なります。
利用者自身でライセンス内容を確認し、遵守してください。

---

## ⚖️ License

This project is licensed under the MIT License.
See [LICENSE](./LICENSE) for details.
