from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_get_settings():
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "sbert_model" in data

def test_update_settings():
    res = client.post("/api/settings", json={
        "key": "cosine_threshold",
        "value": "0.6"
    })
    assert res.status_code == 200


def test_sbert_model_requires_safe_rebuild():
    res = client.post("/api/settings", json={
        "key": "sbert_model",
        "value": "cl-nagoya/ruri-v3-70m"
    })
    assert res.status_code == 409


def test_update_invalid_key():
    res = client.post("/api/settings", json={
        "key": "invalid_key",
        "value": "test"
    })
    assert res.status_code == 400
