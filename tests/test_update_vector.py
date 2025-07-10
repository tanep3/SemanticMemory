from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_update_vector_success():
    r = client.post("/api/add_db", json={"main_text": "ベクトル更新"})
    id_ = str(r.json()["id"])
    client.post("/api/add_vector", json={"id": id_, "text": "旧テキスト"})
    res = client.post("/api/update_vector", json={
        "id": id_,
        "text": "新テキスト",
        "regenerate_summary": True
    })
    assert res.status_code == 200

def test_update_vector_not_found():
    res = client.post("/api/update_vector", json={
        "id": "999999",
        "text": "テスト",
        "regenerate_summary": False
    })
    assert res.status_code == 404
