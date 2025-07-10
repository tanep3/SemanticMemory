import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_search_db_keyword():
    # 検索対象となるデータを作る
    res = client.post("/api/add_db", json={"main_text": "これは検索テスト用のテキストです"})
    assert res.status_code == 200

    # 検索を実行
    res = client.get("/api/search_db?q=検索")
    assert res.status_code == 200
    assert any("検索" in r["main_text"] for r in res.json())

def test_search_db_limit_omitted():
    # 検索対象となるデータを作る
    res = client.post("/api/add_db", json={"main_text": "これは検索テスト用のテキストです"})
    assert res.status_code == 200
    res = client.post("/api/add_db", json={"main_text": "これは検索テスト用のテキストです"})
    assert res.status_code == 200

    # 検索を実行
    res = client.get("/api/search_db?q=検索&limit=1")
    assert res.status_code == 200
    assert len(res.json()) == 1

def test_search_db_limit_zero():
    # 検索対象となるデータを作る
    res = client.post("/api/add_db", json={"main_text": "これは検索テスト用のテキストです"})
    assert res.status_code == 200

    res = client.get("/api/search_db?q=検索&limit=0")
    assert res.status_code == 400

def test_search_db_invalid_order():
    # 検索対象となるデータを作る
    res = client.post("/api/add_db", json={"main_text": "これは検索テスト用のテキストです"})
    assert res.status_code == 200
    res = client.get("/api/search_db?q=検索&order=invalid")
    assert res.status_code == 400
