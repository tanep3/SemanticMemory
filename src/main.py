from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from . import db
from . import settings
from .api_router import router as api_router
from dotenv import load_dotenv
import contextlib
import os

load_dotenv()

# アプリ起動時処理
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # setup
    db.initialize_db()
    db.initialize_settings()
    
    # v2.0.0: 起動時に1年以上経過したaudit_logsを自動クリーンアップ
    try:
        cleaned = db.cleanup_audit_logs(max_age_days=365)
        if cleaned > 0:
            print(f"[Startup] Cleaned {cleaned} old audit logs (>365 days)")
    except Exception as e:
        print(f"[Startup] Audit log cleanup failed: {e}")
    
    yield
    # teardown

app = FastAPI(
    title="SemanticMemory API",
    description="汎用会話履歴・メモ保存API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS設定（必要に応じて調整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーター
app.include_router(api_router, prefix="/api")

# MCP: stdioラッパー（mcp/semantic_memory.py）経由でmcpoと連携
# 詳細は docs/MCP要件定義書.md 参照

# UIを配信（/で静的ファイルを提供）- 最後にマウント
ui_path = Path(__file__).parent.parent / "ui"
if ui_path.exists():
    # UI認証設定（UI_USERとUI_PASSの両方が設定されている場合のみ有効）
    ui_user = os.getenv("UI_USER", "").strip()
    ui_pass = os.getenv("UI_PASS", "").strip()
    
    if ui_user and ui_pass:
        # Basic認証付きでUIを配信
        from starlette.middleware.authentication import AuthenticationMiddleware
        from starlette.authentication import AuthenticationBackend, AuthCredentials, SimpleUser, AuthenticationError
        from starlette.responses import Response
        import base64
        import secrets
        
        class BasicAuthBackend(AuthenticationBackend):
            async def authenticate(self, conn):
                if not conn.scope["path"].startswith("/api"):
                    # UI（非API）へのアクセスは認証必須
                    auth = conn.headers.get("Authorization")
                    if not auth:
                        return None
                    try:
                        scheme, credentials = auth.split()
                        if scheme.lower() != "basic":
                            return None
                        decoded = base64.b64decode(credentials).decode("utf-8")
                        username, password = decoded.split(":", 1)
                        if secrets.compare_digest(username, ui_user) and secrets.compare_digest(password, ui_pass):
                            return AuthCredentials(["authenticated"]), SimpleUser(username)
                    except Exception:
                        return None
                return AuthCredentials(["authenticated"]), SimpleUser("api")
        
        @app.middleware("http")
        async def basic_auth_middleware(request, call_next):
            # APIは認証不要、UIは認証必要
            if not request.url.path.startswith("/api"):
                auth = request.headers.get("Authorization")
                if not auth:
                    return Response(
                        content="Unauthorized",
                        status_code=401,
                        headers={"WWW-Authenticate": 'Basic realm="Neural Dive"'}
                    )
                try:
                    scheme, credentials = auth.split()
                    if scheme.lower() != "basic":
                        raise ValueError()
                    decoded = base64.b64decode(credentials).decode("utf-8")
                    username, password = decoded.split(":", 1)
                    if not (secrets.compare_digest(username, ui_user) and secrets.compare_digest(password, ui_pass)):
                        raise ValueError()
                except Exception:
                    return Response(
                        content="Unauthorized",
                        status_code=401,
                        headers={"WWW-Authenticate": 'Basic realm="Neural Dive"'}
                    )
            return await call_next(request)
        
        print(f"[Startup] UI Basic Auth enabled for user: {ui_user}")
    
    app.mount("/", StaticFiles(directory=str(ui_path), html=True), name="ui")

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("APP_PORT", "6001"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port)