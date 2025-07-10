import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_add_db_main_only():
    res = client.post("/api/add_db", json={"main_text": "テスト"})
    assert res.status_code == 200
    assert "id" in res.json()

def test_add_db_all_fields():
    res = client.post("/api/add_db", json={
        "main_text": "メイン",
        "sub_text": "サブ",
        "summary_text": "要約"
    })
    assert res.status_code == 200

def test_add_db_empty_main():
    res = client.post("/api/add_db", json={"main_text": ""})
    assert res.status_code == 400
