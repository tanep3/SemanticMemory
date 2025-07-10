from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_summarize_basic():
    res = client.post("/api/summarize", json={
        "text": "これは要約のテスト用文章です。"
    })
    assert res.status_code == 200
    assert "summary" in res.json()

def test_summarize_custom_model():
    res = client.post("/api/summarize", json={
        "text": "これは要約テスト。",
        "llm_model": "hf.co/SakanaAI/TinySwallow-1.5B-Instruct-GGUF:Q8_0"
    })
    assert res.status_code == 200
