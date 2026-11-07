from app.db import SessionLocal
from app.models import AuditLog, User
from app.security import hash_password
from tests.test_auth import register, login_headers
from tests.test_documents import upload


def make_admin(client, name="boss", pw="password123"):
    with SessionLocal() as db:
        db.add(User(username=name, password_hash=hash_password(pw), role="admin"))
        db.commit()
    return login_headers(client, name, pw)


def test_normal_user_refused_on_every_admin_route_and_it_is_logged(client):
    register(client, "bob")
    bob = login_headers(client, "bob")
    calls = [("get", "/admin/activity"), ("get", "/admin/audit/verify"), ("get", "/admin/users"),
             ("post", "/admin/users/1/deactivate"), ("post", "/admin/users/1/activate"),
             ("patch", "/admin/users/1/role")]
    for method, url in calls:
        r = client.request(method, url, headers=bob, json={"role": "admin"})
        assert r.status_code == 404, url
    with SessionLocal() as db:
        n = db.query(AuditLog).filter_by(action="admin_access", result="refused").count()
        assert n == len(calls)


def test_admin_routes_need_a_token(client):
    assert client.get("/admin/activity").status_code == 401
    assert client.get("/admin/users").status_code == 401


def test_admin_sees_uploads_and_refused_downloads(client):
    register(client, "alice")
    register(client, "bob")
    a, b = login_headers(client, "alice"), login_headers(client, "bob")
    doc_id = upload(client, a).json()["id"]
    client.get(f"/documents/{doc_id}/download", headers=b)  # refused
    admin = make_admin(client)
    rows = client.get("/admin/activity", headers=admin).json()
    assert any(r["action"] == "upload" and r["document_id"] == doc_id for r in rows)
    refused = client.get("/admin/activity?result=refused&action=download", headers=admin).json()
    assert len(refused) == 1 and refused[0]["document_id"] == doc_id


def test_admin_has_no_automatic_access_to_document_contents(client):
    register(client, "alice")
    a = login_headers(client, "alice")
    doc_id = upload(client, a).json()["id"]
    admin = make_admin(client)
    assert client.get(f"/documents/{doc_id}", headers=admin).status_code == 404
    assert client.get(f"/documents/{doc_id}/download", headers=admin).status_code == 404


def test_deactivation_ends_sessions_immediately_and_blocks_login(client):
    register(client, "bob")
    bob = login_headers(client, "bob")
    admin = make_admin(client)
    bob_id = client.get("/auth/me", headers=bob).json()["id"]
    assert client.post(f"/admin/users/{bob_id}/deactivate", headers=admin).status_code == 200
    assert client.get("/auth/me", headers=bob).status_code == 401  # very next request
    login = client.post("/auth/login", json={"username": "bob", "password": "password123"})
    assert login.status_code == 401
    assert client.post(f"/admin/users/{bob_id}/activate", headers=admin).status_code == 200
    assert client.post("/auth/login", json={"username": "bob", "password": "password123"}).status_code == 200


def test_admin_cannot_deactivate_self(client):
    admin = make_admin(client)
    my_id = client.get("/auth/me", headers=admin).json()["id"]
    assert client.post(f"/admin/users/{my_id}/deactivate", headers=admin).status_code == 400


def test_promotion_works_and_own_role_cannot_change(client):
    register(client, "bob")
    bob = login_headers(client, "bob")
    admin = make_admin(client)
    bob_id = client.get("/auth/me", headers=bob).json()["id"]
    assert client.get("/admin/users", headers=bob).status_code == 404
    r = client.patch(f"/admin/users/{bob_id}/role", headers=admin, json={"role": "admin"})
    assert r.status_code == 200
    assert client.get("/admin/users", headers=bob).status_code == 200
    my_id = client.get("/auth/me", headers=admin).json()["id"]
    assert client.patch(f"/admin/users/{my_id}/role", headers=admin, json={"role": "user"}).status_code == 400


def test_admin_changes_are_audited(client):
    register(client, "bob")
    bob = login_headers(client, "bob")
    admin = make_admin(client)
    bob_id = client.get("/auth/me", headers=bob).json()["id"]
    client.post(f"/admin/users/{bob_id}/deactivate", headers=admin)
    client.patch(f"/admin/users/{bob_id}/role", headers=admin, json={"role": "admin"})
    with SessionLocal() as db:
        assert db.query(AuditLog).filter_by(action="deactivate_user").count() == 1
        assert db.query(AuditLog).filter_by(action="change_role").count() == 1


def test_verify_endpoint_detects_tampering(client):
    admin = make_admin(client)
    assert client.get("/admin/audit/verify", headers=admin).json()["intact"] is True
    with SessionLocal() as db:
        row = db.query(AuditLog).order_by(AuditLog.id).first()
        row.details = "edited later"
        db.commit()
        row_id = row.id
    body = client.get("/admin/audit/verify", headers=admin).json()
    assert body["intact"] is False and body["first_bad_row_id"] == row_id

def test_deactivation_deletes_session_rows(client):
    from app.models import LoginSession
    register(client, "bob")
    bob = login_headers(client, "bob")
    admin = make_admin(client)
    bob_id = client.get("/auth/me", headers=bob).json()["id"]
    client.post(f"/admin/users/{bob_id}/deactivate", headers=admin)
    with SessionLocal() as db:
        assert db.query(LoginSession).filter_by(user_id=bob_id).count() == 0

def test_admin_document_directory_shows_metadata_but_not_titles(client):
    register(client, "alice")
    a = login_headers(client, "alice")
    doc_id = upload(client, a).json()["id"]
    admin = make_admin(client)
    r = client.get("/admin/documents", headers=admin)
    assert r.status_code == 200
    row = next(d for d in r.json() if d["id"] == doc_id)
    assert row["owner_username"] == "alice"
    assert "title" not in row and "original_name" not in row
    assert client.get("/admin/documents", headers=a).status_code == 404