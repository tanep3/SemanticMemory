from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_rebuild_vector_basic():
    res = client.post("/api/rebuild_vector", json={
        "sbert_model": "cl-nagoya/ruri-small-v2",
        "regenerate_summary": True
    })
    assert res.status_code == 200
