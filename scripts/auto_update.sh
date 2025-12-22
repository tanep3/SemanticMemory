#!/bin/bash

# このスクリプトのあるディレクトリの親ディレクトリ（プロジェクトルート）に移動
cd "$(dirname "$0")/.."

# 現在のブランチ名を取得
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "Checking for updates on branch: $BRANCH..."

# リモートの最新情報を取得
git fetch origin

# ローカルとリモートのハッシュを比較
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "🔄 Update found! Starting update process..."
    
    # 1. 最新コードを取得
    echo "📥 Pulling latest changes..."
    git pull origin $BRANCH
    
    # 2. コンテナを再構築・再起動
    echo "🐳 Rebuilding and restarting Docker containers..."
    docker compose down
    docker compose up -d --build
    
    echo "✅ Update complete! System is running with the latest version."
else
    echo "✨ System is already up to date."
fi
