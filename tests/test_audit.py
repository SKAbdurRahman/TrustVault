from app.audit import verify_chain
from app.db import SessionLocal
from app.models import AuditLog
from tests.test_auth import register


def test_refused_login_is_logged_and_chain_is_valid(client):
    register(client)
    client.post("/auth/login", json={"username": "alice", "password": "wrongpass1"})
    with SessionLocal() as db:
        refused = db.query(AuditLog).filter_by(action="login", result="refused").count()
        assert refused == 1
        assert verify_chain(db) == (True, None)


def test_tampering_is_detected(client):
    register(client)
    client.post("/auth/login", json={"username": "alice", "password": "password123"})
    with SessionLocal() as db:
        row = db.query(AuditLog).first()
        row.details = "edited later"
        db.commit()
        ok, bad_id = verify_chain(db)
        assert ok is False and bad_id == row.id