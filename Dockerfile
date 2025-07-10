# ベースイメージ
FROM python:3.12-slim

# 作業ディレクトリ
WORKDIR /app

# Python依存ファイルをコピー
COPY requirements.txt ./

# 必要パッケージインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリのコードをコピー
COPY . .

# 環境変数（必要に応じて）
ENV PYTHONUNBUFFERED=1 \
    CHROMA_PATH=/app/datas/chroma

# ポート開放（FastAPI標準）
EXPOSE 8000

# サービス起動
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
