import os
import threading
import uuid
from contextlib import contextmanager

from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("CHROMA_PATH", "./datas/chroma/")
DEVICE = os.getenv("SBERT_DEVICE", "cpu").strip() or "cpu"
COLLECTION_NAME = "semantic_memory"

_current_model_name = None
_embedding_model = None
_collection_lock = threading.RLock()


@contextmanager
def embedding_state():
    """Serialize operations that must observe one model/collection state."""
    with _collection_lock:
        yield


def get_embedding_model(model_name: str) -> SentenceTransformer:
    global _current_model_name, _embedding_model
    if _embedding_model is None or model_name != _current_model_name:
        _embedding_model = SentenceTransformer(
            model_name,
            device=DEVICE,
            trust_remote_code=True,
        )
        _current_model_name = model_name
    return _embedding_model

# Chromaクライアントとコレクションを再初期化する関数
def init_chroma():
    global client, collection
    client = PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(COLLECTION_NAME)

# 初期化（起動時）
init_chroma()

def _prefix_scheme(model_name):
    if model_name.startswith("cl-nagoya/ruri-v3-"):
        return "ruri_v3_retrieval"
    if model_name.startswith("cl-nagoya/ruri-"):
        return "ruri_v2_retrieval"
    return "none"


def _prefix_texts(texts, scheme, input_type):
    prefixes = {
        ("ruri_v2_retrieval", "query"): "クエリ: ",
        ("ruri_v2_retrieval", "document"): "文章: ",
        ("ruri_v3_retrieval", "query"): "検索クエリ: ",
        ("ruri_v3_retrieval", "document"): "検索文書: ",
    }
    prefix = prefixes.get((scheme, input_type), "")
    return [f"{prefix}{text}" for text in texts]


def _active_prefix_scheme():
    metadata = collection.metadata or {}
    return metadata.get("prefix_scheme", "legacy")


def embed_texts(texts, model, *, input_type=None, prefix_scheme=None):
    prepared = texts
    if input_type:
        scheme = prefix_scheme or _active_prefix_scheme()
        prepared = _prefix_texts(texts, scheme, input_type)
    return model.encode(
        prepared,
        normalize_embeddings=True,
    ).tolist()


def embed_documents(texts, model):
    return embed_texts(texts, model, input_type="document")


def embed_query(text, model):
    return embed_texts([text], model, input_type="query")[0]


# ベクトル追加
def add_vector(id_, text, embedding):
    with _collection_lock:
        existing = collection.get(ids=[str(id_)])
        if existing and existing["ids"]:
            raise HTTPException(status_code=409, detail="Embedding already exists for this id")
        collection.add(
            ids=[str(id_)],
            documents=[text],
            embeddings=[embedding],
        )

# ベクトル検索
def search_vectors(query_embedding, threshold=0.5, limit=10):
    with _collection_lock:
        if limit:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
            )
        else:
            results = collection.query(query_embeddings=[query_embedding])
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
    with _collection_lock:
        collection.delete(ids=[str(id_)])

# 全削除（削除して再初期化）
def clear_collection():
    global client, collection
    with _collection_lock:
        client.delete_collection(name=COLLECTION_NAME)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)

def vector_exists(id_):
    with _collection_lock:
        result = collection.get(ids=[str(id_)])
        return result is not None and result["ids"] and len(result["ids"]) > 0


# 整合性チェック：talk_logsの全IDがChromaに存在するか確認
def check_integrity(db_ids, target_collection=None):
    """
    SQLiteのIDリストに対し、Chroma側に対応するembedding_idが存在するかチェックする。
    Returns: dict {"ok": bool, "db_only": list, "chroma_only": list, "matched": int}
    """
    selected = target_collection or collection
    db_id_set = {str(i) for i in db_ids}
    with _collection_lock:
        all_in_chroma = selected.get(include=[])
        all_chroma_ids = set(all_in_chroma["ids"] or [])
        if db_id_set:
            chroma_for_db = selected.get(ids=list(db_id_set), include=[])
            chroma_found = set(chroma_for_db["ids"] or [])
        else:
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


def rebuild_collection(records, model_name, on_activate=None, batch_size=32):
    """Build a complete replacement and activate it only after validation."""
    global collection

    record_ids = [str(record["id"]) for record in records]
    stage_name = f"semantic-memory-rebuild-{uuid.uuid4().hex[:12]}"
    backup_name = f"semantic-memory-backup-{uuid.uuid4().hex[:12]}"
    model = get_embedding_model(model_name)
    prefix_scheme = _prefix_scheme(model_name)
    get_dimension = getattr(model, "get_embedding_dimension", None)
    if get_dimension is None:
        get_dimension = model.get_sentence_embedding_dimension
    dimension = int(get_dimension())

    with _collection_lock:
        staged = client.create_collection(
            name=stage_name,
            metadata={
                "embedding_model": model_name,
                "embedding_dimension": dimension,
                "prefix_scheme": prefix_scheme,
            },
        )
        activated = False
        try:
            for start in range(0, len(records), batch_size):
                batch = records[start:start + batch_size]
                ids = [str(record["id"]) for record in batch]
                documents = [record["main_text"] for record in batch]
                embeddings = embed_texts(
                    documents,
                    model,
                    input_type="document",
                    prefix_scheme=prefix_scheme,
                )
                staged.add(ids=ids, documents=documents, embeddings=embeddings)

            integrity = check_integrity(record_ids, target_collection=staged)
            if not integrity["ok"]:
                raise RuntimeError(f"staged collection failed integrity check: {integrity}")

            previous = collection
            previous.modify(name=backup_name)
            try:
                staged.modify(name=COLLECTION_NAME)
                collection = staged
                if on_activate:
                    on_activate()
                activated = True
            except Exception:
                collection = previous
                try:
                    staged.modify(name=stage_name)
                finally:
                    previous.modify(name=COLLECTION_NAME)
                raise

            backup_retained = False
            try:
                client.delete_collection(name=backup_name)
            except Exception:
                backup_retained = True
            return {
                "count": len(records),
                "embedding_model": model_name,
                "embedding_dimension": dimension,
                "prefix_scheme": prefix_scheme,
                "integrity": integrity,
                "backup_retained": backup_retained,
                "backup_collection": backup_name if backup_retained else None,
            }
        except Exception:
            if not activated:
                try:
                    client.delete_collection(name=stage_name)
                except Exception:
                    pass
            raise
