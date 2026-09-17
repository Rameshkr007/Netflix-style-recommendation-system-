"""
RecommendationService
------------------------
Owns the lifecycle of the trained HybridRecommender:
  - loads movies + ratings from Postgres into DataFrames
  - fits the hybrid model (content-based + collaborative)
  - exposes recommend_for_user / similar_to / mood-based / explainability
  - caches results in Redis so repeat requests don't recompute

The model is held in-process as a singleton and retrained periodically
(see refresh()) rather than on every request, since fitting TF-IDF + SVD
on every API call would be far too slow. In production this would run on
a schedule (e.g. every N hours via a Celery beat / cron job) rather than
only at process startup.
"""
from __future__ import annotations

import threading

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ml.hybrid import HybridRecommender, Recommendation
from app.models.db_models import Movie, Rating
from app.services.cache import cache_get_json, cache_set_json

settings = get_settings()


class RecommendationService:
    _instance: "RecommendationService | None" = None
    _lock = threading.Lock()

    def __init__(self):
        self.model: HybridRecommender | None = None
        self.movies_df: pd.DataFrame | None = None

    @classmethod
    def get_instance(cls) -> "RecommendationService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def refresh(self, db: Session) -> None:
        """Reload data from Postgres and refit the hybrid model. Thread-safe."""
        with self._lock:
            movies = db.query(Movie).all()
            ratings = db.query(Rating).all()

            self.movies_df = pd.DataFrame([
                {
                    "movieId": m.id,
                    "title": m.title,
                    "genres": m.genres,
                    "director": m.director or "Unknown",
                    "cast": m.cast or "Unknown",
                    "synopsis": m.synopsis or "",
                }
                for m in movies
            ])
            ratings_df = pd.DataFrame([
                {"userId": r.user_id, "movieId": r.movie_id, "rating": r.rating, "timestamp": r.created_at.timestamp()}
                for r in ratings
            ])

            if self.movies_df.empty:
                self.model = None
                return

            if ratings_df.empty:
                # No ratings yet anywhere -- still fit content model so
                # "similar to X" works; collaborative model needs >=1 rating.
                ratings_df = pd.DataFrame(columns=["userId", "movieId", "rating", "timestamp"])
                ratings_df.loc[0] = [0, self.movies_df.iloc[0]["movieId"], 3.0, 0]

            self.model = HybridRecommender(self.movies_df, ratings_df).fit()

    def is_ready(self) -> bool:
        return self.model is not None

    def recommend_for_user(
        self, user_id: int, top_k: int = 10, use_cache: bool = True,
        live_liked_movie_ids: list[int] | None = None,
    ) -> list[Recommendation]:
        cache_key = f"recs:user:{user_id}:k{top_k}"
        if use_cache:
            cached = cache_get_json(cache_key)
            if cached is not None:
                return [Recommendation(**r) for r in cached]

        if not self.model:
            return []

        recs = self.model.recommend(
            user_id, top_k=top_k, alpha=settings.HYBRID_ALPHA_DEFAULT,
            live_liked_movie_ids=live_liked_movie_ids,
        )

        if use_cache:
            cache_set_json(
                cache_key,
                [r.__dict__ for r in recs],
                ttl_seconds=settings.RECOMMENDATION_CACHE_TTL_SECONDS,
            )
        return recs

    def similar_to(self, movie_id: int, top_k: int = 10) -> list[Recommendation]:
        if not self.model:
            return []
        return self.model.recommend_similar_to(movie_id, top_k=top_k)

    def get_movie_row(self, movie_id: int) -> dict | None:
        if self.movies_df is None:
            return None
        row = self.movies_df.loc[self.movies_df.movieId == movie_id]
        return row.iloc[0].to_dict() if not row.empty else None
