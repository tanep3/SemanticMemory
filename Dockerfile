# ベースイメージ
FROM python:3.12-slim

# 作業ディレクトリ
WORKDIR /app

# Python依存ファイルをコピー
COPY requirements.txt ./

# SemanticMemory is CPU-only. Installing torch from PyPI can pull the CUDA
# runtime and several gigabytes of NVIDIA packages even when no GPU exists.
ARG PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 120 --retries 3 \
        --index-url "${PYTORCH_CPU_INDEX_URL}" torch \
    && pip install --timeout 120 --retries 3 -r requirements.txt

# curl (ヘルスチェック用) のインストール
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*


# データディレクトリを作成
RUN mkdir -p ./datas/chroma /root/.cache/huggingface

# アプリのコードをコピー
COPY . .

# 環境変数（必要に応じて）
# HF_HOME: モデルキャッシュをボリュームマウントされたディレクトリに向ける
ENV PYTHONUNBUFFERED=1 \
    CHROMA_PATH=/app/datas/chroma \
    HF_HOME=/root/.cache/huggingface

# サービス起動
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${APP_PORT:-8000}"]
