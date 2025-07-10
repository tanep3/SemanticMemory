from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_save_summarize_false():
    res = client.post("/api/save", json={
        "main_text": "save APIテスト",
        "summarize": False
    })
    assert res.status_code == 200
    assert "id" in res.json()

def test_save_summarize_true():
    res = client.post("/api/save", json={
        "main_text": "save API要約テスト",
        "summarize": True
    })
    assert res.status_code == 200
