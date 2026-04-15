import os
import shutil
from chromadb import PersistentClient
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from fastapi import HTTPException
from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("CHROMA_PATH", "./datas/chroma/")

_current_model_name = None
_embedding_model = None
def get_embedding_model(model_name: str) -> SentenceTransformer:
    global _current_model_name, _embedding_model
    if _embedding_model is None or model_name != _current_model_name:
        _embedding_model = SentenceTransformer(model_name, trust_remote_code=True)
        _current_model_name = model_name
    return _embedding_model

# Chromaクライアントとコレクションを再初期化する関数
def init_chroma():
    global client, collection
    client = PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection("semantic_memory")

# 初期化（起動時）
init_chroma()

# embeddingモデルロード
def load_embedding_model(model_name):
    return SentenceTransformer(model_name, trust_remote_code=True)

# テキスト埋め込み
def embed_texts(texts, model):
    return model.encode(
        texts,
        normalize_embeddings=True
    ).tolist()

# ベクトル追加
def add_vector(id_, text, embedding):
    # 正しい取得
    existing = collection.get(ids=[str(id_)])
    
    if existing and existing["ids"]:
        raise HTTPException(status_code=409, detail="Embedding already exists for this id")
    
    collection.add(
        ids=[str(id_)],
        documents=[text],
        embeddings=[embedding]
    )

# ベクトル検索
def search_vectors(query_embedding, threshold=0.5, limit=10):
    if limit:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
    else:
        results = collection.query(
            query_embeddings=[query_embedding]
        )
    # フィルタリング
    items = []
    for i, distance in enumerate(results['distances'][0]):
        similarity = 1 - (distance / 2)
        if similarity < threshold:
            continue
        items.append({
            "id": results['ids'][0][i],
            "document": results['documents'][0][i],
            "score": similarity
        })
    return items

# ベクトル削除
def delete_vector(id_):
    collection.delete(ids=[str(id_)])

# 全削除（削除して再初期化）
def clear_collection():
    global client, collection
    collection_name = "semantic_memory"
    client.delete_collection(name=collection_name)
    collection = client.get_or_create_collection(name=collection_name)

def vector_exists(id_):
    result = collection.get(ids=[str(id_)])
    return result is not None and result["ids"] and len(result["ids"]) > 0


# 整合性チェック：talk_logsの全IDがChromaに存在するか確認
def check_integrity(db_ids):
    """
    SQLiteのIDリストに対し、Chroma側に対応するembedding_idが存在するかチェックする。
    Returns: dict {"ok": bool, "db_only": list, "chroma_only": list, "matched": int}
    """
    if not db_ids:
        return {"ok": True, "db_only": [], "chroma_only": [], "matched": 0, "total_db": 0, "total_chroma": 0}

    db_id_set = set(str(i) for i in db_ids)

    # Chromaの全embedding_idを取得
    try:
        all_in_chroma = collection.get(include=[])
        all_chroma_ids = set(all_in_chroma["ids"]) if all_in_chroma["ids"] else set()
    except Exception:
        all_chroma_ids = set()

    # DB IDでChromaを検索して存在確認
    try:
        chroma_for_db = collection.get(ids=list(db_id_set), include=[])
        chroma_found = set(chroma_for_db["ids"]) if chroma_for_db["ids"] else set()
    except Exception:
        chroma_found = set()

    matched = db_id_set & chroma_found
    db_only = db_id_set - chroma_found
    chroma_only = all_chroma_ids - db_id_set

    return {
        "ok": len(db_only) == 0 and len(chroma_only) == 0,
        "db_only": sorted(db_only, key=lambda x: int(x) if x.isdigit() else x),
        "chroma_only": sorted(chroma_only, key=lambda x: int(x) if x.isdigit() else x),
        "matched": len(matched),
        "total_db": len(db_id_set),
        "total_chroma": len(all_chroma_ids),
    }

