import os
from starlette.testclient import TestClient
from app.main import app, INDEX_HTML_PATH


def test_cors_headers_on_options():
    client = TestClient(app)
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://trustvault.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://trustvault.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_headers_on_actual_request():
    client = TestClient(app)
    response = client.get(
        "/health",
        headers={"Origin": "https://trustvault.netlify.app"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("access-control-allow-origin") == "https://trustvault.netlify.app"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_root_serves_html_when_index_exists():
    client = TestClient(app)
    assert os.path.isfile(INDEX_HTML_PATH)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "TrustVault" in response.text
    assert "Zero-Trust" in response.text
