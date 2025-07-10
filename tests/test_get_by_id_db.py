import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_get_by_id_existing():
    # まずレコードを作る
    res = client.post("/api/add_db", json={"main_text": "ID取得テスト"})
    assert res.status_code == 200
    id_ = res.json()["id"]

    # 作ったIDを取得
    res = client.get(f"/api/get_by_id_db?id={id_}")
    assert res.status_code == 200
    assert res.json()["main_text"] == "ID取得テスト"

def test_get_by_id_not_found():
    res = client.get("/api/get_by_id_db?id=999999")
    assert res.status_code == 404
