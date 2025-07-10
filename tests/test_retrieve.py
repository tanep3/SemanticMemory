from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_retrieve_query_and_recent():
    # データ仕込み
    r = client.post("/api/add_db", json={"main_text": "retrieve APIテスト"})
    id_ = str(r.json()["id"])
    client.post("/api/add_vector", json={"id": id_, "text": "retrieve APIテスト"})
    res = client.post("/api/retrieve", json={
        "query": "retrieve",
        "threshold": 0.0,
        "limit": 3,
        "recent_limit": 3
    })
    assert res.status_code == 200
    data = res.json()
    assert "semantic" in data
    assert "recent" in data

def test_retrieve_query_only():
    r = client.post("/api/add_db", json={"main_text": "意味検索のみ"})
    id_ = str(r.json()["id"])
    client.post("/api/add_vector", json={"id": id_, "text": "意味検索のみ"})
    res = client.post("/api/retrieve", json={
        "query": "意味検索",
        "threshold": 0.0,
        "limit": 3
    })
    assert res.status_code == 200

def test_retrieve_no_results():
    res = client.post("/api/retrieve", json={
        "query": "絶対ヒットしない文字列",
        "threshold": 0.9,
        "limit": 3,
        "recent_limit": 0
    })
    assert res.status_code == 200
    assert len(res.json()["semantic"]) == 0
