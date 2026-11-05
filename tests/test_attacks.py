from tests.test_auth import register, login_headers
from tests.test_documents import upload
from tests.test_grants import three_users, grant


def test_cannot_revoke_a_grant_through_another_document(client):
    a, b, c = three_users(client)
    doc1 = upload(client, a).json()["id"]
    doc2 = upload(client, b).json()["id"]
    g = grant(client, b, doc2, "carol").json()
    r = client.delete(f"/documents/{doc1}/grants/{g['id']}", headers=a)  # alice uses her own doc path
    assert r.status_code == 404
    assert client.get(f"/documents/{doc2}/download", headers=c).status_code == 200


def test_grant_with_timezone_aware_expiry_does_not_crash(client):
    a, _, _ = three_users(client)
    doc_id = upload(client, a).json()["id"]
    r = grant(client, a, doc_id, "bob", expires_at="2099-01-01T00:00:00Z")
    assert r.status_code in (201, 400, 422)


def test_grant_with_past_expiry_refused(client):
    a, _, _ = three_users(client)
    doc_id = upload(client, a).json()["id"]
    assert grant(client, a, doc_id, "bob", expires_at="2000-01-01T00:00:00").status_code == 400


def test_bad_grant_requests(client):
    a, _, _ = three_users(client)
    doc_id = upload(client, a).json()["id"]
    assert grant(client, a, doc_id, "nobody").status_code == 404
    assert grant(client, a, doc_id, "alice").status_code == 400      # owner to self
    assert grant(client, a, doc_id, "bob", "delete").status_code == 422


def test_html_upload_is_served_as_plain_text_attachment(client):
    a, _, _ = three_users(client)
    r = upload(client, a, data=b"<html><script>alert(1)</script></html>", name="x.html")
    assert r.status_code == 201
    d = client.get(f"/documents/{r.json()['id']}/download", headers=a)
    assert d.headers["content-type"].startswith("text/plain")
    assert "attachment" in d.headers["content-disposition"]
    assert d.headers["x-content-type-options"] == "nosniff"


def test_search_wildcards_do_not_widen_access(client):
    a, b, _ = three_users(client)
    upload(client, a, title="alice secret")
    assert client.get("/documents?q=%25", headers=b).json() == []
    assert client.get("/documents?q=_", headers=b).json() == []


def test_odd_document_ids_are_just_not_found(client):
    a, _, _ = three_users(client)
    for bad in ("0", "-1"):
        assert client.get(f"/documents/{bad}", headers=a).status_code in (404, 422)


def test_garbage_and_wrong_scheme_tokens_rejected(client):
    for h in ({"Authorization": "Bearer abc"}, {"Authorization": "Basic abc"}):
        assert client.get("/auth/me", headers=h).status_code == 401

def test_huge_ids_are_rejected_not_crashed(client):
    a, _, _ = three_users(client)
    for url in ("/documents/99999999999999999999",
                "/documents/99999999999999999999/download",
                "/documents/99999999999999999999/grants"):
        assert client.get(url, headers=a).status_code in (404, 422)