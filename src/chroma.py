import os
import shutil
from chromadb import Client
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from fastapi import HTTPException

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
    client = Client(Settings(
        persist_directory=DB_PATH
    ))
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
def search_vectors(query_embedding, threshold=0.5, limit=5):
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit
    )
    # フィルタリング
    items = []
    for i, distance in enumerate(results['distances'][0]):
        similarity = 1 - distance
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

# 全削除（物理削除して再初期化）
def clear_collection():
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)
    # 再初期化
    init_chroma()

def vector_exists(id_):
    result = collection.get(ids=[str(id_)])
    return result is not None and result["ids"] and len(result["ids"]) > 0

