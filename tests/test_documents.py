import io
from tests.test_auth import register, login_headers

PDF = b"%PDF-1.4 hello"


def setup_two_users(client):
    register(client, "alice")
    register(client, "bob")
    return login_headers(client, "alice"), login_headers(client, "bob")


def upload(client, headers, data=PDF, name="a.pdf", title="Secret"):
    return client.post("/documents", headers=headers, data={"title": title},
                       files={"file": (name, io.BytesIO(data), "application/pdf")})


def test_owner_can_upload_and_download(client):
    a, _ = setup_two_users(client)
    doc = upload(client, a).json()
    r = client.get(f"/documents/{doc['id']}/download", headers=a)
    assert r.status_code == 200 and r.content == PDF


def test_other_user_refused_on_every_route(client):
    a, b = setup_two_users(client)
    doc_id = upload(client, a).json()["id"]
    assert client.get(f"/documents/{doc_id}", headers=b).status_code == 404
    assert client.get(f"/documents/{doc_id}/download", headers=b).status_code == 404


def test_no_token_refused(client):
    a, _ = setup_two_users(client)
    doc_id = upload(client, a).json()["id"]
    assert client.get(f"/documents/{doc_id}/download").status_code == 401
    assert client.get("/documents").status_code == 401


def test_unknown_document_looks_same_as_forbidden(client):
    a, b = setup_two_users(client)
    doc_id = upload(client, a).json()["id"]
    forbidden = client.get(f"/documents/{doc_id}", headers=b)
    missing = client.get("/documents/99999", headers=b)
    assert forbidden.status_code == missing.status_code == 404
    assert forbidden.json() == missing.json()


def test_search_and_list_never_show_other_users_documents(client):
    a, b = setup_two_users(client)
    upload(client, a, title="Salary letters")
    assert client.get("/documents", headers=b).json() == []
    assert client.get("/documents?q=Salary", headers=b).json() == []
    assert len(client.get("/documents?q=Salary", headers=a).json()) == 1


def test_refused_download_is_audited(client):
    from app.db import SessionLocal
    from app.models import AuditLog
    a, b = setup_two_users(client)
    doc_id = upload(client, a).json()["id"]
    client.get(f"/documents/{doc_id}/download", headers=b)
    with SessionLocal() as db:
        n = db.query(AuditLog).filter_by(action="download", result="refused").count()
        assert n == 1


def test_fake_extension_rejected(client):
    a, _ = setup_two_users(client)
    r = upload(client, a, data=b"MZ\x90\x00\x03\x00\x00\x00 binary", name="virus.pdf")
    assert r.status_code == 415


def test_oversized_file_rejected(client):
    a, _ = setup_two_users(client)
    r = upload(client, a, data=b"%PDF-" + b"x" * (5 * 1024 * 1024))
    assert r.status_code == 413


def test_path_traversal_name_is_harmless(client):
    a, _ = setup_two_users(client)
    r = upload(client, a, name="../../etc/passwd.pdf")
    assert r.status_code == 201
    assert "/" not in r.json()["original_name"] and ".." not in r.json()["original_name"].split("passwd")[0]

def test_successful_download_is_audited(client):
    from app.db import SessionLocal
    from app.models import AuditLog
    a, _ = setup_two_users(client)
    doc_id = upload(client, a).json()["id"]
    client.get(f"/documents/{doc_id}/download", headers=a)
    with SessionLocal() as db:
        n = db.query(AuditLog).filter_by(action="download", result="allowed", document_id=doc_id).count()
        assert n == 1