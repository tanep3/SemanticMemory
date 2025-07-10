from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from . import settings
from .api_router import router as api_router
from dotenv import load_dotenv
import contextlib

load_dotenv()

# アプリ起動時処理
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # setup
    db.initialize_db()
    db.initialize_settings()
    yield
    # teardown

app = FastAPI(
    title="SemanticMemory API",
    description="汎用会話履歴・メモ保存API",
    version="1.0.0",
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
