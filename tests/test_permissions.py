import uuid
from datetime import timedelta
from app.db import SessionLocal
from app.models import User, Document, Grant, now
from app.permissions import can


def _user(db, name, role="user"):
    u = User(username=name, password_hash="x", role=role)
    db.add(u); db.commit()
    return u


def _doc(db, owner):
    d = Document(owner_id=owner.id, title="t", stored_name=uuid.uuid4().hex,
                 original_name="a.txt", content_type="text/plain", size=1)
    db.add(d); db.commit()
    return d


def _grant(db, doc, user, permission, **kw):
    g = Grant(document_id=doc.id, user_id=user.id, permission=permission,
              granted_by=doc.owner_id, **kw)
    db.add(g); db.commit()
    return g


def test_permission_matrix():
    with SessionLocal() as db:
        owner, stranger = _user(db, "owner"), _user(db, "stranger")
        reader, editor = _user(db, "reader"), _user(db, "editor")
        admin = _user(db, "boss", role="admin")
        doc = _doc(db, owner)
        _grant(db, doc, reader, "read")
        _grant(db, doc, editor, "edit")

        for action in ("read", "download", "edit", "delete", "grant"):
            assert can(db, owner, doc, action)
            assert not can(db, stranger, doc, action)
            assert not can(db, admin, doc, action)  # admin has no automatic access

        assert can(db, reader, doc, "read") and can(db, reader, doc, "download")
        assert not can(db, reader, doc, "edit")
        assert can(db, editor, doc, "edit")
        for action in ("delete", "grant"):
            assert not can(db, reader, doc, action)
            assert not can(db, editor, doc, action)


def test_revoked_and_expired_grants_stop_working():
    with SessionLocal() as db:
        owner, a, b = _user(db, "o"), _user(db, "a"), _user(db, "b")
        doc = _doc(db, owner)
        g = _grant(db, doc, a, "read")
        assert can(db, a, doc, "read")
        g.revoked_at = now(); db.commit()
        assert not can(db, a, doc, "read")  # takes effect on the very next check

        _grant(db, doc, b, "read", expires_at=now() - timedelta(seconds=1))
        assert not can(db, b, doc, "read")


def test_deleted_document_and_unknown_action_denied():
    with SessionLocal() as db:
        owner = _user(db, "o")
        doc = _doc(db, owner)
        assert not can(db, owner, doc, "fly")
        doc.deleted_at = now(); db.commit()
        assert not can(db, owner, doc, "read")