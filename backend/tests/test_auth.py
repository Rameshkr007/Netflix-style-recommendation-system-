def test_register_creates_user_and_returns_token(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "alice@example.com",
        "password": "StrongPass123!",
        "display_name": "Alice",
        "favorite_genres": ["Drama", "Sci-Fi"],
    })
    assert r.status_code == 201
    assert "access_token" in r.json()


def test_register_duplicate_email_rejected(client):
    payload = {
        "email": "bob@example.com",
        "password": "StrongPass123!",
        "display_name": "Bob",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 400


def test_login_with_correct_credentials_succeeds(client):
    client.post("/api/v1/auth/register", json={
        "email": "carol@example.com", "password": "StrongPass123!", "display_name": "Carol",
    })
    r = client.post("/api/v1/auth/login", json={"email": "carol@example.com", "password": "StrongPass123!"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_with_wrong_password_rejected(client):
    client.post("/api/v1/auth/register", json={
        "email": "dave@example.com", "password": "StrongPass123!", "display_name": "Dave",
    })
    r = client.post("/api/v1/auth/login", json={"email": "dave@example.com", "password": "WrongPassword!"})
    assert r.status_code == 401


def test_me_requires_authentication(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "erin@example.com", "password": "StrongPass123!", "display_name": "Erin",
    })
    token = r.json()["access_token"]
    r2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == "erin@example.com"


def test_non_admin_cannot_access_admin_routes(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "frank@example.com", "password": "StrongPass123!", "display_name": "Frank",
    })
    token = r.json()["access_token"]
    r2 = client.get("/api/v1/admin/analytics/overview", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 403
