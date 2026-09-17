"""
Tests for new advanced features:
- NCF inference wrapper
- Refresh token rotation
- Google OAuth error handling
- Redis Pub/Sub manager
- WebSocket endpoint
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Refresh Token Rotation ─────────────────────────────────────────────────

def test_refresh_token_returned_on_login(client):
    """Login should return both access + refresh tokens."""
    client.post("/api/v1/auth/register", json={
        "email": "refresh_test@example.com",
        "password": "RefreshTest123!",
        "display_name": "RefreshTest",
    })
    r = client.post("/api/v1/auth/login", json={
        "email": "refresh_test@example.com",
        "password": "RefreshTest123!",
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != data["access_token"]


def test_refresh_token_grants_new_access_token(client):
    """A valid refresh token should return a new access + refresh token pair."""
    import time
    client.post("/api/v1/auth/register", json={
        "email": "rotate@example.com",
        "password": "Rotate1234!",
        "display_name": "Rotate",
    })
    login_r = client.post("/api/v1/auth/login", json={
        "email": "rotate@example.com",
        "password": "Rotate1234!",
    })
    old_refresh = login_r.json()["refresh_token"]

    # Wait 1s so iat differs — JWT iat has 1-second resolution
    time.sleep(1.1)

    r = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # After 1s wait, tokens MUST differ
    assert data["access_token"]  != old_refresh
    assert data["refresh_token"] != old_refresh


def test_expired_refresh_token_rejected(client):
    """A tampered or invalid refresh token should be rejected with 401."""
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
    assert r.status_code == 401


def test_register_also_returns_refresh_token(client):
    """Registration should return refresh token immediately (no second login needed)."""
    r = client.post("/api/v1/auth/register", json={
        "email": "newuser_refresh@example.com",
        "password": "NewUser1234!",
        "display_name": "NewUser",
    })
    assert r.status_code == 201
    data = r.json()
    assert "refresh_token" in data


# ── Google OAuth Error Handling ────────────────────────────────────────────

def test_google_login_without_client_id_configured_returns_400(client):
    """When GOOGLE_CLIENT_ID is not set, /auth/google should return 400."""
    r = client.post("/api/v1/auth/google", json={"id_token": "fake.google.token"})
    # Should fail gracefully (400 = config not set, not 500 = crash)
    assert r.status_code in (400, 501)
    data = r.json()
    assert "detail" in data


def test_google_login_with_invalid_token_returns_400(client, monkeypatch):
    """An invalid Google ID token should return 400, not 500."""
    # Patch GOOGLE_CLIENT_ID to something so we get past the config check
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "fake-client-id-123.apps.googleusercontent.com")

    r = client.post("/api/v1/auth/google", json={"id_token": "definitely.not.a.real.token"})
    assert r.status_code == 400
    assert "detail" in r.json()


# ── NCF Inference ─────────────────────────────────────────────────────────

def test_ncf_inference_loads_if_model_exists():
    """NCF inference wrapper should load the trained model from disk."""
    import os
    model_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "models", "ncf_model.pt"
    )
    if not os.path.exists(model_path):
        pytest.skip("NCF model not trained yet — run scripts/train_neural_cf.py")

    from app.ml.ncf_inference import NCFInference
    ncf = NCFInference(model_path)
    assert ncf.is_available, "NCF model failed to load despite checkpoint existing"


def test_ncf_inference_predicts_valid_rating_range():
    """NCF predictions should be in [0.5, 5.0] range."""
    import os
    model_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "models", "ncf_model.pt"
    )
    if not os.path.exists(model_path):
        pytest.skip("NCF model not trained yet")

    from app.ml.ncf_inference import NCFInference
    import torch
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    user_map = checkpoint["user_map"]
    item_map = checkpoint["item_map"]

    ncf = NCFInference(model_path)
    if not ncf.is_available:
        pytest.skip("NCF failed to load")

    # Pick a known user and item
    user_id = list(user_map.keys())[0]
    movie_id = list(item_map.keys())[0]

    pred = ncf.predict_rating(user_id, movie_id)
    assert pred is not None
    assert 0.5 <= pred <= 5.0, f"Prediction {pred} out of [0.5, 5.0] range"


def test_ncf_inference_batch_returns_dict():
    """Batch prediction should return a dict mapping movie_id → predicted_rating."""
    import os
    model_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "models", "ncf_model.pt"
    )
    if not os.path.exists(model_path):
        pytest.skip("NCF model not trained yet")

    from app.ml.ncf_inference import NCFInference
    import torch
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    user_map  = checkpoint["user_map"]
    item_map  = checkpoint["item_map"]

    ncf = NCFInference(model_path)
    if not ncf.is_available:
        pytest.skip("NCF failed to load")

    user_id   = list(user_map.keys())[0]
    movie_ids = list(item_map.keys())[:5]

    results = ncf.predict_batch(user_id, movie_ids)
    assert isinstance(results, dict)
    assert len(results) == len(movie_ids)
    for mid, rating in results.items():
        assert 0.5 <= rating <= 5.0


def test_ncf_returns_none_for_unknown_user():
    """NCF should return None for users not in training data."""
    import os
    model_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "models", "ncf_model.pt"
    )
    if not os.path.exists(model_path):
        pytest.skip("NCF model not trained yet")

    from app.ml.ncf_inference import NCFInference
    import torch
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    item_map = checkpoint["item_map"]

    ncf = NCFInference(model_path)
    if not ncf.is_available:
        pytest.skip("NCF failed to load")

    movie_id = list(item_map.keys())[0]
    result = ncf.predict_rating(user_id=999999, movie_id=movie_id)
    assert result is None


# ── Hybrid + NCF integration ───────────────────────────────────────────────

def test_hybrid_recommendations_still_work_with_ncf_loaded(seeded_client):
    """Hybrid recommendations should work correctly with NCF wired in."""
    r = seeded_client.post("/api/v1/auth/register", json={
        "email": "ncf_integration@example.com",
        "password": "NcfTest1234!",
        "display_name": "NcfTest",
    })
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Rate some movies
    movies = seeded_client.get("/api/v1/movies?limit=5").json()
    for m in movies[:4]:
        seeded_client.post("/api/v1/movies/rate",
                           json={"movie_id": m["id"], "rating": 5.0},
                           headers=headers)

    # Refresh model
    import sqlite3, os
    # Promote to admin
    db_path = None
    for var, val in os.environ.items():
        if "sqlite" in val.lower() and val.startswith("sqlite:///"):
            db_path = val.replace("sqlite:///", "")
    if db_path:
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE users SET role='ADMIN' WHERE email='ncf_integration@example.com'")
        conn.commit(); conn.close()

    r2 = seeded_client.post("/api/v1/auth/login", json={
        "email": "ncf_integration@example.com", "password": "NcfTest1234!"
    })
    admin_headers = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    refresh_r = seeded_client.post("/api/v1/admin/model/refresh", headers=admin_headers)
    assert refresh_r.status_code == 200

    # Get recommendations
    recs_r = seeded_client.get("/api/v1/recommendations/for-me?top_k=5", headers=headers)
    assert recs_r.status_code == 200
    recs = recs_r.json()
    assert len(recs) > 0
    # Source should be hybrid (or hybrid+ncf if model loaded)
    for rec in recs:
        assert rec["source"] in ("hybrid", "hybrid+ncf", "popularity")


# ── WebSocket endpoint ─────────────────────────────────────────────────────

def test_websocket_connects_and_receives_welcome(client):
    """WebSocket /ws/live should accept connection and send welcome message."""
    with client.websocket_connect("/ws/live") as ws:
        data = ws.receive_json()
        assert data["type"] == "connected"
        assert "channel" in data
        assert "active_connections" in data


def test_websocket_responds_to_ping(client):
    """WebSocket should respond to ping with pong."""
    with client.websocket_connect("/ws/live") as ws:
        ws.receive_json()  # welcome message
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_websocket_channel_selection(client):
    """WebSocket should accept channel query parameter."""
    with client.websocket_connect("/ws/live?channel=system") as ws:
        data = ws.receive_json()
        assert data["type"] == "connected"
        assert data["channel"] == "system"
