import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_update_db_main():
    res = client.post("/api/add_db", json={"main_text": "更新前"})
    assert res.status_code == 200
    id_ = res.json()["id"]

    res = client.patch("/api/update_db", json={
        "id": id_,
        "main_text": "更新後"
    })
    assert res.status_code == 200


def test_update_db_all_fields():
    # レコードを作る
    res = client.post("/api/add_db", json={"main_text": "all update"})
    assert res.status_code == 200
    id_ = res.json()["id"]

    # 全部更新
    res = client.patch("/api/update_db", json={
        "id": id_,
        "main_text": "main updated",
        "sub_text": "sub updated",
        "summary_text": "summary updated"
    })
    assert res.status_code == 200
