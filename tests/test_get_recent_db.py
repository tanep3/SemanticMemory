import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.fixture
def setup_data():
    # 必要な初期化
    client.post("/api/add_db", json={"main_text": "test data 1"})
    client.post("/api/add_db", json={"main_text": "test data 2"})
    return True

def test_get_recent_limit():
    # テスト前に複数レコードを仕込む
    for i in range(3):
        res = client.post("/api/add_db", json={"main_text": f"recent test {i}"})
        assert res.status_code == 200

    res = client.get("/api/get_recent_db?limit=2")
    assert res.status_code == 200
    assert len(res.json()) == 2

def test_get_recent_no_limit():
    # データをさらに仕込む
    for i in range(5):
        res = client.post("/api/add_db", json={"main_text": f"recent no limit {i}"})
        assert res.status_code == 200

    res = client.get("/api/get_recent_db")
    assert res.status_code == 200
    assert len(res.json()) >= 3

def test_get_recent_limit_zero(setup_data):
    res = client.get("/api/get_recent_db?limit=0")
    assert res.status_code == 400
