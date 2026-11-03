import io
from tests.test_auth import register, login_headers
from tests.test_documents import upload, PDF


def three_users(client):
    for n in ("alice", "bob", "carol"):
        register(client, n)
    return [login_headers(client, n) for n in ("alice", "bob", "carol")]


def grant(client, headers, doc_id, username, permission="read", **extra):
    return client.post(f"/documents/{doc_id}/grants", headers=headers,
                       json={"username": username, "permission": permission, **extra})


def test_grant_gives_access_and_revoke_removes_it_immediately(client):
    a, b, _ = three_users(client)
    doc_id = upload(client, a).json()["id"]
    assert client.get(f"/documents/{doc_id}/download", headers=b).status_code == 404
    g = grant(client, a, doc_id, "bob")
    assert g.status_code == 201
    assert client.get(f"/documents/{doc_id}/download", headers=b).status_code == 200
    assert client.delete(f"/documents/{doc_id}/grants/{g.json()['id']}", headers=a).status_code == 200
    assert client.get(f"/documents/{doc_id}/download", headers=b).status_code == 404  # very next request


def test_viewer_cannot_grant_revoke_list_edit_or_delete(client):
    a, b, _ = three_users(client)
    doc_id = upload(client, a).json()["id"]
    g = grant(client, a, doc_id, "bob", "read").json()
    assert grant(client, b, doc_id, "carol").status_code == 404
    assert grant(client, b, doc_id, "bob", "edit").status_code == 404  # cannot upgrade self
    assert client.get(f"/documents/{doc_id}/grants", headers=b).status_code == 404
    assert client.delete(f"/documents/{doc_id}/grants/{g['id']}", headers=b).status_code == 404
    assert client.patch(f"/documents/{doc_id}", headers=b, data={"title": "x"}).status_code == 404
    assert client.delete(f"/documents/{doc_id}", headers=b).status_code == 404


def test_editor_can_edit_but_not_delete_or_grant(client):
    a, b, _ = three_users(client)
    doc_id = upload(client, a).json()["id"]
    grant(client, a, doc_id, "bob", "edit")
    assert client.patch(f"/documents/{doc_id}", headers=b, data={"title": "New"}).status_code == 200
    assert client.delete(f"/documents/{doc_id}", headers=b).status_code == 404
    assert grant(client, b, doc_id, "carol").status_code == 404


def test_stranger_cannot_edit_or_delete(client):
    a, _, c = three_users(client)
    doc_id = upload(client, a).json()["id"]
    assert client.patch(f"/documents/{doc_id}", headers=c, data={"title": "x"}).status_code == 404
    assert client.delete(f"/documents/{doc_id}", headers=c).status_code == 404


def test_delete_makes_document_unreachable_for_everyone(client):
    a, b, _ = three_users(client)
    doc_id = upload(client, a).json()["id"]
    grant(client, a, doc_id, "bob")
    assert client.delete(f"/documents/{doc_id}", headers=a).status_code == 200
    assert client.get(f"/documents/{doc_id}", headers=a).status_code == 404
    assert client.get(f"/documents/{doc_id}/download", headers=b).status_code == 404
    assert client.get("/documents", headers=a).json() == []


def test_grant_and_revoke_are_audited(client):
    from app.db import SessionLocal
    from app.models import AuditLog
    a, b, _ = three_users(client)
    doc_id = upload(client, a).json()["id"]
    g = grant(client, a, doc_id, "bob").json()
    client.delete(f"/documents/{doc_id}/grants/{g['id']}", headers=a)
    grant(client, b, doc_id, "carol")  # refused
    with SessionLocal() as db:
        assert db.query(AuditLog).filter_by(action="grant", result="allowed").count() == 1
        assert db.query(AuditLog).filter_by(action="revoke", result="allowed").count() == 1
        assert db.query(AuditLog).filter_by(action="grant", result="refused").count() == 1


def test_expired_grant_does_not_work(client):
    from app.db import SessionLocal
    from app.models import Grant, now
    from datetime import timedelta
    a, b, _ = three_users(client)
    doc_id = upload(client, a).json()["id"]
    g = grant(client, a, doc_id, "bob").json()
    with SessionLocal() as db:
        row = db.get(Grant, g["id"])
        row.expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert client.get(f"/documents/{doc_id}/download", headers=b).status_code == 404