# ベースイメージ
FROM python:3.12-slim

# 作業ディレクトリ
WORKDIR /app

# Python依存ファイルをコピー
COPY requirements.txt ./

# 必要パッケージインストール
RUN pip install --no-cache-dir -r requirements.txt

# データディレクトリを作成
RUN mkdir -p ./datas/chroma

# アプリのコードをコピー
COPY . .

# 環境変数（必要に応じて）
ENV PYTHONUNBUFFERED=1 \
    CHROMA_PATH=/app/datas/chroma

# サービス起動
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${APP_PORT:-8000}"]
