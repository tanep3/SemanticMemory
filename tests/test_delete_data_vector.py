from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_delete_data_vector_success():
    r = client.post("/api/add_db", json={"main_text": "削除対象"})
    id_ = str(r.json()["id"])
    client.post("/api/add_vector", json={"id": id_, "text": "削除テキスト"})
    res = client.delete("/api/delete_data_vector?id={id_}")
    assert res.status_code == 200

def test_delete_data_vector_not_found():
    res = client.delete("/api/delete_data_vecto?id=999999")
    assert res.status_code == 404
