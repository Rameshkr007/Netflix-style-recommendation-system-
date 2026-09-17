def _register_and_rate(client, n_movies=5, rating=5.0, email="recuser@example.com"):
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "StrongPass123!", "display_name": "Rec User",
    })
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    movies = client.get(f"/api/v1/movies?limit={n_movies}").json()
    for m in movies:
        client.post("/api/v1/movies/rate", json={"movie_id": m["id"], "rating": rating}, headers=headers)
    return headers


def test_for_me_recommendations_for_cold_start_user_returns_popularity(seeded_client):
    r = seeded_client.post("/api/v1/auth/register", json={
        "email": "newbie@example.com", "password": "StrongPass123!", "display_name": "Newbie",
    })
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r2 = seeded_client.get("/api/v1/recommendations/for-me?top_k=5", headers=headers)
    assert r2.status_code == 200
    recs = r2.json()
    assert len(recs) > 0
    assert recs[0]["source"] == "popularity"


def test_for_me_recommendations_after_rating_returns_hybrid(seeded_client):
    headers = _register_and_rate(seeded_client)
    r = seeded_client.get("/api/v1/recommendations/for-me?top_k=5", headers=headers)
    assert r.status_code == 200
    recs = r.json()
    assert len(recs) > 0
    for rec in recs:
        assert rec["source"] == "hybrid"
        assert "reason" in rec
        assert isinstance(rec["score"], float)


def test_for_me_requires_auth(seeded_client):
    r = seeded_client.get("/api/v1/recommendations/for-me")
    assert r.status_code == 401


def test_mood_recommendations_returns_relevant_genres(seeded_client):
    r = seeded_client.post("/api/v1/recommendations/mood", json={"mood_text": "I feel really scared, give me something spooky"})
    assert r.status_code == 200
    movies = r.json()
    assert len(movies) > 0
    # at least some results should touch horror/thriller/mystery genres
    genre_hits = sum(
        1 for m in movies if any(g in m["genres"] for g in ["Horror", "Thriller", "Mystery"])
    )
    assert genre_hits > 0


def test_trending_endpoint_returns_movies(seeded_client):
    r = seeded_client.get("/api/v1/recommendations/trending?limit=10")
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_taste_dna_with_no_ratings(seeded_client):
    r = seeded_client.post("/api/v1/auth/register", json={
        "email": "blank@example.com", "password": "StrongPass123!", "display_name": "Blank",
    })
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r2 = seeded_client.get("/api/v1/recommendations/taste-dna", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["total_rated"] == 0


def test_taste_dna_after_rating(seeded_client):
    headers = _register_and_rate(seeded_client, n_movies=4)
    r = seeded_client.get("/api/v1/recommendations/taste-dna", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_rated"] == 4
    assert "viewing_personality" in data
    assert len(data["genre_breakdown"]) > 0
