# ベースイメージ
FROM python:3.12-slim

# 作業ディレクトリ
WORKDIR /app

# Python依存ファイルをコピー
COPY requirements.txt ./

# 必要パッケージインストール (BuildKit cacheを使用)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# データディレクトリを作成
RUN mkdir -p ./datas/chroma ./datas/huggingface

# アプリのコードをコピー
COPY . .

# 環境変数（必要に応じて）
# HF_HOME: モデルキャッシュをボリュームマウントされたディレクトリに向ける
ENV PYTHONUNBUFFERED=1 \
    CHROMA_PATH=/app/datas/chroma \
    HF_HOME=/app/datas/huggingface

# サービス起動
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${APP_PORT:-8000}"]
