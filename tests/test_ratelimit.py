from datetime import timedelta
from app.db import SessionLocal
from app.models import AuditLog, LoginAttempt, now
from tests.test_auth import register, login_headers


def bad(client, name="alice", ip=None):
    headers = {"x-forwarded-for": ip} if ip else {}
    return client.post("/auth/login", json={"username": name, "password": "wrongpass1"}, headers=headers)


def good(client, name="alice"):
    return client.post("/auth/login", json={"username": name, "password": "password123"})


def test_locked_after_five_failures_even_with_correct_password(client):
    register(client)
    for _ in range(5):
        assert bad(client).status_code == 401
    assert bad(client).status_code == 429
    assert good(client).status_code == 429


def test_success_resets_the_counter(client):
    register(client)
    for _ in range(4):
        bad(client)
    assert good(client).status_code == 200
    for _ in range(4):
        assert bad(client).status_code == 401


def test_other_usernames_are_unaffected(client):
    register(client)
    register(client, "bob")
    for _ in range(6):
        bad(client)
    assert good(client, "bob").status_code == 200


def test_unknown_username_is_throttled_too(client):
    for _ in range(5):
        assert bad(client, "ghost").status_code == 401
    assert bad(client, "ghost").status_code == 429


def test_per_ip_limit_across_many_usernames(client):
    for i in range(20):
        bad(client, f"user{i}", ip="9.9.9.9")
    assert bad(client, "another", ip="9.9.9.9").status_code == 429
    assert bad(client, "another", ip="8.8.8.8").status_code == 401


def test_lockout_expires_after_the_window(client):
    register(client)
    for _ in range(5):
        bad(client)
    assert good(client).status_code == 429
    with SessionLocal() as db:
        for a in db.query(LoginAttempt).all():
            a.time = now() - timedelta(minutes=16)
        db.commit()
    assert good(client).status_code == 200


def test_lockout_is_audited_once(client):
    register(client)
    for _ in range(8):
        bad(client)
    with SessionLocal() as db:
        assert db.query(AuditLog).filter_by(action="login_lockout").count() == 1