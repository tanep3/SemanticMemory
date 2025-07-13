from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List

from . import db
from . import chroma
from . import ollama
from . import settings
from .chroma import get_embedding_model, embed_texts

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

# -----------------------------
# /api/add_db
# -----------------------------
@router.post("/add_db")
def add_db(req: AddDBRequest):
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
    limit: Optional[int] = None
):
    if limit == 0:
        raise HTTPException(status_code=400, detail="limit must be >0 or omitted")
    
    return db.get_recent_talk_logs(order=order, limit=limit)

# -----------------------------
# /api/get_by_id_db
# -----------------------------
@router.get("/get_by_id_db")
def get_by_id_db(id: int):
    record = db.get_talk_log_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record

# -----------------------------
# /api/delete_data_db
# -----------------------------
@router.delete("/delete_data_db")
def delete_data_db(id: int):
    count = db.delete_talk_log(id)
    if count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": id, "status": "deleted"}

# -----------------------------
# /api/delete_data_vector
# -----------------------------
@router.delete("/delete_data_vector")
def delete_data_vector(id: str):
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
    if sbert_model is None:
        sbert_model = settings.get_setting("sbert_model")
    model = get_embedding_model(sbert_model)
    records = db.get_recent_talk_logs()
    chroma.clear_collection()
    for r in records:
        emb = embed_texts([r["main_text"]], model)[0]
        chroma.add_vector(str(r["id"]), r["main_text"], emb)
    return {"status": "rebuild completed", "count": len(records)}

# -----------------------------
# /api/summarize
# -----------------------------
@router.post("/summarize")
def summarize(req: SummarizeRequest):
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
    return settings.get_all_settings()

@router.post("/settings")
def update_setting(req: SettingsUpdateRequest):
    try:
        settings.update_setting(req.key, req.value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key")
    return {"key": req.key, "value": req.value, "status": "updated"}
