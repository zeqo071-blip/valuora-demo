from fastapi.testclient import TestClient
from app import config, main

config.DB_PATH = ":memory:" if False else "/tmp/valuora_test.db"


def test_flow():
    with TestClient(main.app) as c:
        assert c.get("/").status_code == 200
        r = c.post("/register", data={"email": "a@b.az", "password": "12345678"}, follow_redirects=False)
        assert r.status_code == 303
        assert c.get("/dashboard").status_code == 200
        assert c.post("/analyze", data={"url": "http://127.0.0.1"}).status_code == 400
