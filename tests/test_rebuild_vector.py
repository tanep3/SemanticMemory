import numpy as np
from fastapi.testclient import TestClient

from src import chroma, db, settings
from src.main import app

client = TestClient(app)


class FakeEmbeddingModel:
    def get_sentence_embedding_dimension(self):
        return 3

    def encode(self, texts, normalize_embeddings=True):
        vectors = []
        for index, _ in enumerate(texts, start=1):
            vector = np.array([index, index + 1, index + 2], dtype=float)
            if normalize_embeddings:
                vector /= np.linalg.norm(vector)
            vectors.append(vector)
        return np.array(vectors)


def test_rebuild_vector_activates_validated_collection(monkeypatch):
    db.insert_talk_log("右を向いたら机が見えた")
    db.insert_talk_log("昨日は雨だった")
    monkeypatch.setattr(chroma, "get_embedding_model", lambda _: FakeEmbeddingModel())

    res = client.post(
        "/api/rebuild_vector",
        params={
            "sbert_model": "cl-nagoya/ruri-v3-70m",
            "regenerate_summary": False,
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 2
    assert data["embedding_dimension"] == 3
    assert data["prefix_scheme"] == "ruri_v3_retrieval"
    assert data["integrity"]["ok"] is True
    assert settings.get_setting("sbert_model") == "cl-nagoya/ruri-v3-70m"
    assert chroma.collection.metadata["embedding_model"] == "cl-nagoya/ruri-v3-70m"
