import os
from starlette.testclient import TestClient
from app.main import app, INDEX_HTML_PATH


def test_cors_headers_on_options():
    client = TestClient(app)
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://frabjous-puppy-0abe47.netlify.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://frabjous-puppy-0abe47.netlify.app"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_headers_on_actual_request():
    client = TestClient(app)
    response = client.get(
        "/health",
        headers={"Origin": "https://frabjous-puppy-0abe47.netlify.app"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("access-control-allow-origin") == "https://frabjous-puppy-0abe47.netlify.app"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_root_serves_html_when_index_exists():
    client = TestClient(app)
    assert os.path.isfile(INDEX_HTML_PATH)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "TrustVault" in response.text
    assert "Zero-Trust" in response.text


def test_demo_passwords_in_index_html():
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Ur@owner7" in content
    assert "Theyr@viewers2" in content
    assert "Iam@admin2" in content
    assert "OwnerPass123!" not in content


def test_cors_blocks_unknown_origin():
    client = TestClient(app)
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers