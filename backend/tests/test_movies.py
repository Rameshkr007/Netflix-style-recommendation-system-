def _register(client, email="user@example.com"):
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "StrongPass123!", "display_name": "User",
    })
    return r.json()["access_token"]


def test_list_movies_returns_seeded_catalog(seeded_client):
    r = seeded_client.get("/api/v1/movies?limit=10")
    assert r.status_code == 200
    movies = r.json()
    assert len(movies) == 10
    assert "title" in movies[0]


def test_list_movies_filter_by_genre(seeded_client):
    r = seeded_client.get("/api/v1/movies?genre=Horror&limit=50")
    assert r.status_code == 200
    for m in r.json():
        assert "Horror" in m["genres"]


def test_get_single_movie(seeded_client):
    movies = seeded_client.get("/api/v1/movies?limit=1").json()
    movie_id = movies[0]["id"]
    r = seeded_client.get(f"/api/v1/movies/{movie_id}")
    assert r.status_code == 200
    assert r.json()["id"] == movie_id


def test_get_nonexistent_movie_returns_404(seeded_client):
    r = seeded_client.get("/api/v1/movies/999999")
    assert r.status_code == 404


def test_rate_movie_requires_auth(seeded_client):
    movies = seeded_client.get("/api/v1/movies?limit=1").json()
    r = seeded_client.post("/api/v1/movies/rate", json={"movie_id": movies[0]["id"], "rating": 4.5})
    assert r.status_code == 401


def test_rate_movie_then_update_rating(seeded_client):
    token = _register(seeded_client)
    headers = {"Authorization": f"Bearer {token}"}
    movies = seeded_client.get("/api/v1/movies?limit=1").json()
    movie_id = movies[0]["id"]

    r1 = seeded_client.post("/api/v1/movies/rate", json={"movie_id": movie_id, "rating": 3.0}, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["rating"] == 3.0

    r2 = seeded_client.post("/api/v1/movies/rate", json={"movie_id": movie_id, "rating": 5.0}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["rating"] == 5.0  # update, not a duplicate row


def test_rating_out_of_range_rejected(seeded_client):
    token = _register(seeded_client)
    headers = {"Authorization": f"Bearer {token}"}
    movies = seeded_client.get("/api/v1/movies?limit=1").json()
    r = seeded_client.post("/api/v1/movies/rate", json={"movie_id": movies[0]["id"], "rating": 9.0}, headers=headers)
    assert r.status_code == 422


def test_watchlist_add_list_remove(seeded_client):
    token = _register(seeded_client)
    headers = {"Authorization": f"Bearer {token}"}
    movies = seeded_client.get("/api/v1/movies?limit=1").json()
    movie_id = movies[0]["id"]

    r = seeded_client.post("/api/v1/movies/watchlist", json={"movie_id": movie_id}, headers=headers)
    assert r.status_code == 204

    r2 = seeded_client.get("/api/v1/movies/me/watchlist", headers=headers)
    assert any(m["id"] == movie_id for m in r2.json())

    r3 = seeded_client.delete(f"/api/v1/movies/watchlist/{movie_id}", headers=headers)
    assert r3.status_code == 204

    r4 = seeded_client.get("/api/v1/movies/me/watchlist", headers=headers)
    assert all(m["id"] != movie_id for m in r4.json())


def test_similar_movies_endpoint(seeded_client):
    movies = seeded_client.get("/api/v1/movies?limit=1").json()
    r = seeded_client.get(f"/api/v1/movies/{movies[0]['id']}/similar?top_k=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
