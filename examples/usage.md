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
python ai_sample.py
```

### 設定
スクリプト内の以下の変数を環境に合わせて変更してください。

```python
# API設定
API_URL = "http://localhost:6001/api"

# AI設定 (Ollama)
OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "gemini-3-flash-preview:cloud" # 利用可能なモデル名に変更
```

---

## 2. OpenWebUI フィルター (`open_webui_filter.py`)

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
Functionを有効化すると、歯車アイコン（Settings）から以下の項目を設定できます。コードを書き換える必要はありません。

- **api_url**: SemanticMemory APIのURL
    - OpenWebUIがDockerで動いている場合、ホストのAPIには `http://host.docker.internal:6001/api` などでアクセスします。
- **search_limit**: 検索する過去の記憶の数（デフォルト: `10`）
- **threshold**: ベクトル検索の類似度しきい値（デフォルト: `0.6`）
    - `0.0`〜`1.0` の範囲。高いほど厳密に一致するものだけを採用します。
- **auto_save**: 会話の自動保存を有効にするか（デフォルト: `True`）
