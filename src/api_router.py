from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List

from . import db
from . import chroma
from . import ollama
from . import settings
from .chroma import get_embedding_model, embed_texts, check_integrity

router = APIRouter()

# -----------------------------
# モデル
# -----------------------------

class AddDBRequest(BaseModel):
    main_text: str
    sub_text: Optional[str] = None
    summary_text: Optional[str] = None

class AddVectorRequest(BaseModel):
    id: str
    text: str

class SearchDBResponse(BaseModel):
    id: int
    main_text: str
    sub_text: Optional[str]
    summary_text: Optional[str]
    create_time: str
    update_time: Optional[str]

class SearchVectorRequest(BaseModel):
    query: str
    threshold: Optional[float] = None
    limit: Optional[int] = None

class UpdateDBRequest(BaseModel):
    id: int
    main_text: Optional[str]
    sub_text: Optional[str] = None
    summary_text: Optional[str] = None

class UpdateVectorRequest(BaseModel):
    id: str
    text: str
    regenerate_summary: Optional[bool] = False

class SummarizeRequest(BaseModel):
    text: str
    llm_model: Optional[str] = None

class SaveRequest(BaseModel):
    main_text: str
    sub_text: Optional[str] = None
    original_text: Optional[str] = None
    summarize: Optional[bool] = True

class RetrieveRequest(BaseModel):
    query: Optional[str]
    threshold: Optional[float] = None
    limit: Optional[int] = None
    recent_limit: Optional[int] = None

class SettingsUpdateRequest(BaseModel):
    key: str
    value: str

# v2.0.0 モデル
class UpdateMemoryRequest(BaseModel):
    id: int
    main_text: Optional[str] = None
    sub_text: Optional[str] = None
    summary_text: Optional[str] = None

class CleanupAuditLogsRequest(BaseModel):
    max_age_days: Optional[int] = None  # None = 全削除

# -----------------------------
# /api/add_db
# -----------------------------
@router.post("/add_db")
def add_db(req: AddDBRequest):
    """SQLiteにテキストデータを新規登録する。"""
    if not req.main_text:
        raise HTTPException(status_code=400, detail="main_text is required")
    id_ = db.insert_talk_log(
        main_text=req.main_text,
        sub_text=req.sub_text,
        summary_text=req.summary_text
    )
    return {"id": id_, "status": "saved"}

# -----------------------------
# /api/add_vector
# -----------------------------
@router.post("/add_vector")
def add_vector(req: AddVectorRequest):
    """ベクトルDB（Chroma）にテキストを埋め込み登録する。"""
    model_name = settings.get_setting("sbert_model")
    model = get_embedding_model(model_name)
    emb = embed_texts([req.text], model)[0]
    chroma.add_vector(req.id, req.text, emb)
    return {"id": req.id, "status": "vector saved"}

# -----------------------------
# /api/search_db
# -----------------------------
@router.get("/search_db", response_model=List[SearchDBResponse])
def search_db(q: str, order: str = "desc", limit: Optional[int] = None):
    """SQLiteの全文検索（LIKE検索）。"""
    if not q:
        raise HTTPException(status_code=400, detail="q is required")
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="order must be asc or desc")
    if limit == 0:
        raise HTTPException(status_code=400, detail="limit must be >0 or omitted")
    return db.search_talk_logs(q, order=order, limit=limit)

# -----------------------------
# /api/search_vector
# -----------------------------
@router.post("/search_vector")
def search_vector(req: SearchVectorRequest):
    """ベクトルDB（Chroma）で意味検索を実行する。"""
    if not req.query:
        raise HTTPException(status_code=400, detail="query is required")
    if req.limit == 0:
        raise HTTPException(status_code=400, detail="limit must be >0 or omitted")

    sbert_model = settings.get_setting("sbert_model")
    model = get_embedding_model(sbert_model)
    emb = embed_texts([req.query], model)[0]
    if req.threshold:
        threshold = float(req.threshold)
    else:
        threshold = float(settings.get_setting("cosine_threshold"))

    results = chroma.search_vectors(
        query_embedding=emb,
        threshold=threshold,
        limit=req.limit
    )

    return results

# -----------------------------
# /api/get_recent_db
# -----------------------------
@router.get("/get_recent_db", response_model=List[SearchDBResponse])
def get_recent_db(
    order: str = Query("create", enum=["create", "update"]),
    limit: Optional[int] = None,
    offset: int = 0
):
    """最近のデータを時系列で取得する（ページネーション対応）。"""
    if limit == 0:
        raise HTTPException(status_code=400, detail="limit must be >0 or omitted")
    
    return db.get_recent_talk_logs(order=order, limit=limit, offset=offset)

# -----------------------------
# /api/get_by_id_db
# -----------------------------
@router.get("/get_by_id_db")
def get_by_id_db(id: int):
    """指定IDのデータを1件取得する。"""
    record = db.get_talk_log_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record

# -----------------------------
# /api/delete_data_db
# -----------------------------
@router.delete("/delete_data_db")
def delete_data_db(id: int):
    """SQLiteから指定IDのデータを削除する。"""
    count = db.delete_talk_log(id)
    if count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": id, "status": "deleted"}

# -----------------------------
# /api/delete_data_vector
# -----------------------------
@router.delete("/delete_data_vector")
def delete_data_vector(id: str):
    """ベクトルDB（Chroma）から指定IDのデータを削除する。"""
    try:
        chroma.delete_vector(id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": id, "status": "vector deleted"}

# -----------------------------
# /api/update_db
# -----------------------------
@router.patch("/update_db")
def update_db(req: UpdateDBRequest):
    """SQLiteのデータを更新する。"""
    if not (req.main_text or req.sub_text or req.summary_text):
        raise HTTPException(status_code=400, detail="No fields to update")
    count = db.update_talk_log(
        req.id,
        main_text=req.main_text,
        sub_text=req.sub_text,
        summary_text=req.summary_text
    )
    if count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": req.id, "status": "updated"}

# -----------------------------
# /api/update_vector
# -----------------------------
@router.post("/update_vector")
def update_vector(req: UpdateVectorRequest):
    """ベクトルDB（Chroma）のデータを削除して再埋め込みする。"""
    exists = chroma.vector_exists(req.id)
    # 存在確認
    if not chroma.vector_exists(req.id):
        raise HTTPException(status_code=404, detail="Vector not found")

    # 削除
    chroma.delete_vector(req.id)

    # 再追加
    model_name = settings.get_setting("sbert_model")
    model = get_embedding_model(model_name)
    emb = embed_texts([req.text], model)[0]
    chroma.add_vector(req.id, req.text, emb)

    summary = None
    if req.regenerate_summary:
        llm_model = settings.get_setting("llm_model")
        url = settings.get_setting("ollama_url")
        summary = ollama.summarize_text(req.text, model=llm_model, url=url)

    return {"id": req.id, "status": "vector updated", "summary": summary}

# -----------------------------
# /api/rebuild_vector
# -----------------------------
@router.post("/rebuild_vector")
def rebuild_vector(sbert_model: Optional[str] = None, regenerate_summary: bool = False):
    """SQLiteの全データからベクトルDBを再構築する（モデル変更時等）。
    改善点: 事後の整合性チェックを行い、結果を返す。
    """
    if sbert_model is None:
        sbert_model = settings.get_setting("sbert_model")
    model = get_embedding_model(sbert_model)
    records = db.get_recent_talk_logs()

    # 事前チェック
    pre_check = chroma.check_integrity([r["id"] for r in records]) if records else {"ok": True}

    chroma.clear_collection()
    success = 0
    fail = 0
    for r in records:
        try:
            emb = embed_texts([r["main_text"]], model)[0]
            chroma.add_vector(str(r["id"]), r["main_text"], emb)
            success += 1
        except Exception as e:
            fail += 1

    # 事後チェック
    post_records = db.get_recent_talk_logs()
    post_check = chroma.check_integrity([r["id"] for r in post_records]) if post_records else {"ok": True}

    return {
        "status": "rebuild completed",
        "count": len(records),
        "success": success,
        "fail": fail,
        "pre_integrity": pre_check,
        "post_integrity": post_check,
        "integrity_ok": post_check.get("ok", False),
    }


# -----------------------------
# /api/check_integrity (v2.1.0)
# -----------------------------
@router.get("/check_integrity")
def check_integrity():
    """
    SQLiteとChromaDBのID整合性をチェックする。
    データ復旧や不具合診断に使用。
    """
    records = db.get_recent_talk_logs(limit=10000)
    db_ids = [r["id"] for r in records]
    result = chroma.check_integrity(db_ids)
    result["details"] = {
        "db_count": len(db_ids),
        "db_id_range": f"{min(db_ids)}-{max(db_ids)}" if db_ids else "N/A",
        "chroma_count": result.get("total_chroma", 0),
    }
    return result

# -----------------------------
# /api/summarize
# -----------------------------
@router.post("/summarize")
def summarize(req: SummarizeRequest):
    """Ollamaを使ってテキストを要約する。"""
    model = req.llm_model or settings.get_setting("llm_model")
    url = settings.get_setting("ollama_url")
    system_prompt = settings.get_setting("system_prompt")
    summary = ollama.summarize_text(req.text, system_prompt=system_prompt, model=model, url=url)
    return {"summary": summary}

# -----------------------------
# /api/save
# -----------------------------
@router.post("/save")
def save(req: SaveRequest):
    """SQLiteとベクトルDBに同時保存する（要約自動生成可）。"""
    summary_text = None
    if req.summarize:
        llm_model = settings.get_setting("llm_model")
        url = settings.get_setting("ollama_url")
        target_text = req.original_text or req.main_text        
        summary_text = ollama.summarize_text(target_text, model=llm_model, url=url)

    id_ = db.insert_talk_log(
        main_text=req.main_text,
        sub_text=req.sub_text,
        summary_text=summary_text
    )

    sbert_model = settings.get_setting("sbert_model")
    model = get_embedding_model(sbert_model)
    emb = embed_texts([req.main_text], model)[0]
    chroma.add_vector(str(id_), req.main_text, emb)

    return {"id": id_, "status": "saved"}

# -----------------------------
# /api/retrieve
# -----------------------------
@router.post("/retrieve")
def retrieve(req: RetrieveRequest):
    """意味検索（Vector）と直近履歴（SQLite）を併合して取得する。"""
    sbert_model = settings.get_setting("sbert_model")
    model = get_embedding_model(sbert_model)
    if req.threshold:
        threshold = float(req.threshold)
    else:
        threshold = float(settings.get_setting("cosine_threshold"))
    if req.limit:
        limit = req.limit
    else:
        limit = int(settings.get_setting("recall_limit"))
    semantic_results = []
    if req.query:
        emb = embed_texts([req.query], model)[0]
        semantic_results = chroma.search_vectors(
            query_embedding=emb,
            threshold=threshold,
            limit=limit
        )
    recent_results = db.get_recent_talk_logs(limit=req.recent_limit or 5)
    return {
        "semantic": semantic_results,
        "recent": recent_results
    }

# -----------------------------
# /api/settings
# -----------------------------
@router.get("/settings")
def get_all_settings():
    """現在の設定値を全て取得する。"""
    return settings.get_all_settings()

@router.post("/settings")
def update_setting(req: SettingsUpdateRequest):
    """設定値を更新する。"""
    try:
        settings.update_setting(req.key, req.value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key")
    return {"key": req.key, "value": req.value, "status": "updated"}

# -----------------------------
# v2.0.0 統合エンドポイント
# -----------------------------

@router.patch("/update_memory")
def update_memory(req: UpdateMemoryRequest):
    """
    SQLite + Chroma 統合更新。
    main_text変更時はVector再埋め込み + サマリー自動再生成。
    """
    # 既存レコード取得
    record = db.get_talk_log_by_id(req.id)
    if not record:
        raise HTTPException(status_code=404, detail="Memory not found")

    # 更新データ準備
    update_main = req.main_text if req.main_text is not None else None
    update_sub = req.sub_text if req.sub_text is not None else None
    update_summary = req.summary_text if req.summary_text is not None else None

    # main_textが変更された場合、Vector再埋め込み + サマリー再生成
    new_summary = None
    if update_main is not None and update_main != record["main_text"]:
        # Vector再埋め込み
        sbert_model = settings.get_setting("sbert_model")
        model = get_embedding_model(sbert_model)
        emb = embed_texts([update_main], model)[0]
        
        # 古いVector削除して再追加
        try:
            chroma.delete_vector(str(req.id))
        except Exception:
            pass
        chroma.add_vector(str(req.id), update_main, emb)

        # サマリー再生成
        llm_model = settings.get_setting("llm_model")
        url = settings.get_setting("ollama_url")
        new_summary = ollama.summarize_text(update_main, model=llm_model, url=url)
        update_summary = new_summary

    # DB更新
    if update_main or update_sub or update_summary:
        db.update_talk_log(
            req.id,
            main_text=update_main,
            sub_text=update_sub,
            summary_text=update_summary
        )

    return {
        "id": req.id,
        "status": "updated",
        "summary_regenerated": new_summary is not None,
        "new_summary": new_summary
    }


@router.delete("/delete_memory")
def delete_memory(id: int):
    """
    SQLite + Chroma 同期削除 + audit_logs記録。
    """
    # 既存レコード取得（削除前にログ用に保存）
    record = db.get_talk_log_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Memory not found")

    # SQLite削除
    db.delete_talk_log(id)

    # Chroma削除
    try:
        chroma.delete_vector(str(id))
    except Exception:
        pass  # Vectorがなくてもエラーにしない

    # 監査ログ記録
    db.insert_audit_log(
        action="DELETE",
        target_id=id,
        deleted_data=record,
        user_agent="API"
    )

    return {"id": id, "status": "deleted"}


@router.post("/cleanup_audit_logs")
def cleanup_audit_logs(req: CleanupAuditLogsRequest = None):
    """
    監査ログをクリーンアップする。
    max_age_days指定時はその日数以上経過したレコードを削除。
    省略時は全削除。
    """
    max_age = req.max_age_days if req else None
    count = db.cleanup_audit_logs(max_age_days=max_age)
    return {
        "status": "cleaned",
        "deleted_count": count,
        "max_age_days": max_age
    }


# -----------------------------
# v2.0.0 MCPエンドポイント
# -----------------------------

class MCPRecallRequest(BaseModel):
    query: str
    limit: int = 3
    threshold: float = 0.7

class MCPDeleteRequest(BaseModel):
    id: int
    confirm: bool = False


@router.post("/mcp/recall_memory")
def mcp_recall_memory(req: MCPRecallRequest):
    """
    【MCPツール】記憶を明示的に思い出す。
    Vector検索でマッチしたIDについて、SQLiteから生データを取得して返す。
    """
    # 1. Vector検索
    sbert_model = settings.get_setting("sbert_model")
    model = get_embedding_model(sbert_model)
    emb = embed_texts([req.query], model)[0]
    
    vector_results = chroma.search_vectors(
        query_embedding=emb,
        threshold=req.threshold,
        limit=req.limit
    )
    
    if not vector_results:
        return {
            "status": "no_results",
            "message": "関連する記憶が見つかりませんでした",
            "memories": []
        }
    
    # 2. 各IDについてSQLiteから生データを取得
    memories = []
    for item in vector_results:
        try:
            record = db.get_talk_log_by_id(int(item["id"]))
            if record:
                record["similarity_score"] = item.get("score", 0)
                memories.append(record)
        except Exception:
            pass
    
    return {
        "status": "success",
        "count": len(memories),
        "memories": memories
    }


@router.post("/mcp/delete_memory")
def mcp_delete_memory(req: MCPDeleteRequest):
    """
    【MCPツール】記憶を削除する（HITL対応）。
    confirm=False: 削除対象の確認（プレビュー）
    confirm=True: 実際に削除を実行
    """
    # 対象の記憶を取得
    record = db.get_talk_log_by_id(req.id)
    if not record:
        return {
            "status": "error",
            "message": f"ID {req.id} の記憶は存在しません"
        }
    
    if not req.confirm:
        # 確認フェーズ: 削除対象の情報を返す
        main_text = record.get("main_text", "")
        return {
            "status": "confirmation_required",
            "message": "削除を実行するには confirm=true を指定してください",
            "memory": {
                "id": record.get("id"),
                "summary_text": record.get("summary_text"),
                "main_text": main_text[:200] + "..." if len(main_text) > 200 else main_text,
                "create_time": record.get("create_time")
            }
        }
    else:
        # 削除フェーズ: 実際に削除
        # SQLite削除
        db.delete_talk_log(req.id)
        
        # Chroma削除
        try:
            chroma.delete_vector(str(req.id))
        except Exception:
            pass
        
        # 監査ログ記録
        db.insert_audit_log(
            action="DELETE",
            target_id=req.id,
            deleted_data=record,
            user_agent="MCP"
        )
        
        return {
            "status": "deleted",
            "message": f"ID {req.id} の記憶を削除しました",
            "deleted_id": req.id
        }

