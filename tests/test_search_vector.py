import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_search_vector_basic():
    res = client.post("/api/add_db", json={"main_text": "意味検索用"})
    assert res.status_code == 200
    id_ = str(res.json()["id"])
    res = client.post("/api/add_vector", json={"id": id_, "text": "意味検索用"})
    assert res.status_code == 200

    res = client.post("/api/search_vector", json={
        "query": "意味検索",
        "threshold": 0.0,
        "limit": 3
    })
    assert res.status_code == 200
    assert any(r["id"] == id_ for r in res.json())

def test_search_vector_limit_omitted():
    res = client.post("/api/add_db", json={"main_text": "意味検索用"})
    id_ = str(res.json()["id"])
    client.post("/api/add_vector", json={"id": id_, "text": "意味検索用"})

    res = client.post("/api/search_vector", json={
        "query": "意味検索",
        "threshold": 0.0
    })
    assert res.status_code == 200

def test_search_vector_limit_zero():
    res = client.post("/api/add_db", json={"main_text": "意味検索用"})
    id_ = str(res.json()["id"])
    client.post("/api/add_vector", json={"id": id_, "text": "意味検索用"})

    res = client.post("/api/search_vector", json={
        "query": "意味検索",
        "threshold": 0.0,
        "limit": 0
    })
    assert res.status_code == 400
