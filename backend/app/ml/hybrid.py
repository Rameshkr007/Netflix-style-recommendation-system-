"""
Hybrid Recommendation Engine
-------------------------------
Blends THREE signals:
  1. Content-Based Filtering (TF-IDF cosine similarity)
  2. Collaborative Filtering (SVD matrix factorization)
  3. Neural CF (GMF+MLP deep learning) — optional, loads from trained checkpoint

Blend: score = alpha * CF_score + (1-alpha) * CB_score
       If NCF available: score = 0.4*NCF + 0.35*CF + 0.25*CB (more weight to NCF)

alpha defaults to 0.6 (favor collaborative), tunable for A/B testing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from app.ml.collaborative import CollaborativeRecommender
from app.ml.content_based import ContentBasedRecommender
from app.ml.ncf_inference import get_ncf_inference

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    movie_id: int
    score: float
    reason: str
    source: str  # "hybrid" | "content" | "collaborative" | "popularity"


class HybridRecommender:
    def __init__(self, movies_df: pd.DataFrame, ratings_df: pd.DataFrame):
        self.movies_df = movies_df
        self.ratings_df = ratings_df
        self.content_model = ContentBasedRecommender(movies_df)
        self.collab_model = CollaborativeRecommender(ratings_df)
        self._popularity_ranking: list[tuple[int, float]] | None = None

    def fit(self) -> "HybridRecommender":
        self.content_model.fit()
        self.collab_model.fit()
        self._build_popularity_ranking()
        return self

    def _build_popularity_ranking(self) -> None:
        stats = (
            self.ratings_df.groupby("movieId")["rating"]
            .agg(["mean", "count"])
            .reset_index()
        )
        # Bayesian-ish weighting: titles with very few ratings shouldn't
        # outrank well-established crowd favorites just from one 5-star vote.
        global_mean = self.ratings_df["rating"].mean()
        min_votes = 5
        stats["weighted_score"] = (
            (stats["count"] / (stats["count"] + min_votes)) * stats["mean"]
            + (min_votes / (stats["count"] + min_votes)) * global_mean
        )
        ranked = stats.sort_values("weighted_score", ascending=False)
        self._popularity_ranking = [
            (int(mid), float(score))
            for mid, score in zip(ranked["movieId"], ranked["weighted_score"])
        ]

    def _user_liked_movies(self, user_id: int, min_rating: float = 4.0) -> list[int]:
        user_ratings = self.ratings_df[self.ratings_df.userId == user_id]
        liked = user_ratings[user_ratings.rating >= min_rating]
        return liked.sort_values("rating", ascending=False)["movieId"].tolist()

    def recommend(
        self,
        user_id: int,
        top_k: int = 10,
        alpha: float = 0.6,
        exclude: set[int] | None = None,
        live_liked_movie_ids: list[int] | None = None,
    ) -> list[Recommendation]:
        """
        live_liked_movie_ids: optionally pass the user's *current* highly-rated
        movie IDs straight from the database. The collaborative model only
        knows about ratings that existed at the last fit() call, so a user
        who just rated their first few titles won't be a "known user" to
        collaborative.py until the next periodic refresh -- but we can still
        give them real content-based recommendations right away by using
        their live ratings here instead of waiting.
        """
        exclude = set(exclude or set())
        is_known = self.collab_model.is_known_user(user_id)
        liked_movies = self._user_liked_movies(user_id) if is_known else []

        if not liked_movies and live_liked_movie_ids:
            liked_movies = [m for m in live_liked_movie_ids if m in self.content_model.movie_id_to_idx]

        if not liked_movies:
            return self._cold_start_recommend(top_k=top_k, exclude=exclude)

        already_seen = set(
            self.ratings_df.loc[self.ratings_df.userId == user_id, "movieId"]
        ) | set(live_liked_movie_ids or [])
        exclude |= already_seen

        # widen the CF candidate pool, then re-rank with content score blended in
        cf_results = dict(self.collab_model.recommend_for_user(
            user_id, top_k=top_k * 4, exclude=exclude
        ))
        cb_results = dict(self.content_model.recommend_for_liked_set(
            liked_movies, top_k=top_k * 4, exclude=exclude
        ))

        # Try to get NCF predictions for candidate movies
        ncf = get_ncf_inference()
        candidates = set(cf_results) | set(cb_results)
        ncf_results: dict[int, float] = {}
        if ncf:
            ncf_results = ncf.predict_batch(user_id, list(candidates))

        blended: list[Recommendation] = []
        for movie_id in candidates:
            movie_id = int(movie_id)
            cf_score  = self._normalize_rating(cf_results.get(movie_id))
            cb_score  = cb_results.get(movie_id, 0.0)
            ncf_score = self._normalize_rating(ncf_results.get(movie_id))

            if ncf_results and movie_id in ncf_results:
                # Three-way blend: NCF gets most weight when available
                final_score = 0.40 * ncf_score + 0.35 * cf_score + 0.25 * cb_score
                source = "hybrid+ncf"
            else:
                final_score = alpha * cf_score + (1 - alpha) * cb_score
                source = "hybrid"

            reason = self._explain(movie_id, liked_movies, in_cf=movie_id in cf_results,
                                    in_cb=movie_id in cb_results)
            blended.append(Recommendation(
                movie_id=movie_id, score=final_score, reason=reason, source=source,
            ))

        blended.sort(key=lambda r: -r.score)
        return blended[:top_k]

    def _cold_start_recommend(self, top_k: int, exclude: set[int]) -> list[Recommendation]:
        """No rating history yet -> recommend by global popularity."""
        results = []
        for movie_id, score in self._popularity_ranking or []:
            if movie_id in exclude:
                continue
            results.append(Recommendation(
                movie_id=movie_id,
                score=float(score),
                reason="Trending now among viewers with similar taste profiles.",
                source="popularity",
            ))
            if len(results) >= top_k:
                break
        return results

    def recommend_similar_to(self, movie_id: int, top_k: int = 10) -> list[Recommendation]:
        """Used for 'Because you watched X' rails — content similarity to a single title."""
        similar = self.content_model.similar_to_movie(movie_id, top_k=top_k)
        return [
            Recommendation(
                movie_id=mid,
                score=score,
                reason=self.content_model.explain_similarity(movie_id, mid),
                source="content",
            )
            for mid, score in similar
        ]

    @staticmethod
    def _normalize_rating(predicted_rating: float | None) -> float:
        """Map a 0.5-5.0 predicted rating onto a roughly 0-1 scale for blending with cosine similarity."""
        if predicted_rating is None:
            return 0.0
        return max(0.0, min(1.0, (predicted_rating - 0.5) / 4.5))

    def _explain(self, movie_id: int, liked_movies: list[int], in_cf: bool, in_cb: bool) -> str:
        if in_cb and liked_movies:
            ref_title = self.movies_df.loc[
                self.movies_df.movieId == liked_movies[0], "title"
            ]
            ref_title_str = ref_title.values[0] if len(ref_title) else "titles you liked"
            base = f"Because you watched {ref_title_str}"
            if in_cf:
                return base + ", and viewers with similar taste also rated this highly."
            return base + "."
        if in_cf:
            return "Viewers with similar taste to you rated this highly."
        return "Recommended for you."
