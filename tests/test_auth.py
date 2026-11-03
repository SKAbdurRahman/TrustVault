def register(client, name="alice", pw="password123", **extra):
    return client.post("/auth/register", json={"username": name, "password": pw, **extra})


def login_headers(client, name="alice", pw="password123"):
    r = client.post("/auth/login", json={"username": name, "password": pw})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_register_login_me(client):
    assert register(client).status_code == 201
    r = client.get("/auth/me", headers=login_headers(client))
    assert r.status_code == 200 and r.json()["username"] == "alice"


def test_wrong_password_rejected(client):
    register(client)
    r = client.post("/auth/login", json={"username": "alice", "password": "wrongpass1"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_logout_revokes_token_immediately(client):
    register(client)
    h = login_headers(client)
    assert client.get("/auth/me", headers=h).status_code == 200
    client.post("/auth/logout", headers=h)
    assert client.get("/auth/me", headers=h).status_code == 401


def test_cannot_self_register_as_admin(client):
    register(client, role="admin")  # extra field must be ignored
    r = client.get("/auth/me", headers=login_headers(client))
    assert r.json()["role"] == "user"


def test_duplicate_username_rejected(client):
    register(client)
    assert register(client).status_code == 409