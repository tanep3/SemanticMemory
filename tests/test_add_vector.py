import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_add_vector_existing_id():
    # まずIDを作成
    res = client.post("/api/add_db", json={"main_text": "埋め込み用"})
    assert res.status_code == 200
    new_id = str(res.json()["id"])

    # 1回目は成功
    res = client.post("/api/add_vector", json={"id": new_id, "text": "ベクトルテキスト"})
    assert res.status_code == 200

    # 2回目はエラー
    res = client.post("/api/add_vector", json={"id": new_id, "text": "ベクトルテキスト"})
    assert res.status_code in (400, 409)

