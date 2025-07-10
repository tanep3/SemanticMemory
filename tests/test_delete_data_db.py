from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_delete_data_db_success():
    # 登録
    r = client.post("/api/add_db", json={"main_text": "削除対象"})
    id_ = r.json()["id"]
    # 削除
    res = client.delete(f"/api/delete_data_db?id={id_}")
    assert res.status_code == 200

def test_delete_data_db_not_found():
    res = client.delete(f"/api/delete_data_db?id={999999}")
    assert res.status_code == 404
