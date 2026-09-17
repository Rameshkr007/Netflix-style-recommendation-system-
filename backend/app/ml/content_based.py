"""
Content-Based Recommendation Engine
------------------------------------
Builds a TF-IDF representation of each title's "content profile" (genres,
director, cast, synopsis) and recommends titles with the highest cosine
similarity to a given title or to a user's liked-titles centroid.

This captures "users who liked X will like Y because Y is similar in content"
-- independent of any rating data, so it works even for brand-new ("cold
start") users and brand-new titles.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ContentBasedRecommender:
    def __init__(self, movies_df: pd.DataFrame):
        self.movies_df = movies_df.reset_index(drop=True)
        self.movie_id_to_idx = {
            int(mid): idx for idx, mid in enumerate(self.movies_df["movieId"])
        }
        self._vectorizer: TfidfVectorizer | None = None
        self._tfidf_matrix = None
        self._similarity_matrix: np.ndarray | None = None

    def _build_content_soup(self) -> pd.Series:
        """Combine genres, director, cast, synopsis into one weighted text blob per title."""
        df = self.movies_df

        def soup(row) -> str:
            genres = row["genres"].replace("|", " ").lower()
            director = row["director"].replace(" ", "").replace(".", "").lower()
            cast = " ".join(
                name.strip().replace(" ", "").lower() for name in row["cast"].split(",")
            )
            synopsis = str(row.get("synopsis", "")).lower()
            # repeat genres x3 and director x2 to weight them higher than free-text synopsis
            return f"{(genres + ' ') * 3}{(director + ' ') * 2}{cast} {synopsis}"

        return df.apply(soup, axis=1)

    def fit(self) -> "ContentBasedRecommender":
        content_soup = self._build_content_soup()
        self._vectorizer = TfidfVectorizer(stop_words="english", min_df=1)
        self._tfidf_matrix = self._vectorizer.fit_transform(content_soup)
        self._similarity_matrix = cosine_similarity(self._tfidf_matrix)
        return self

    def similar_to_movie(self, movie_id: int, top_k: int = 10) -> list[tuple[int, float]]:
        """Return [(movieId, similarity_score), ...] most similar to the given movie."""
        if movie_id not in self.movie_id_to_idx:
            return []
        idx = self.movie_id_to_idx[movie_id]
        scores = self._similarity_matrix[idx]
        ranked = np.argsort(-scores)
        results = []
        for i in ranked:
            if i == idx:
                continue
            results.append((int(self.movies_df.iloc[i]["movieId"]), float(scores[i])))
            if len(results) >= top_k:
                break
        return results

    def recommend_for_liked_set(
        self, liked_movie_ids: list[int], top_k: int = 10, exclude: set[int] | None = None
    ) -> list[tuple[int, float]]:
        """
        Build a centroid profile vector from all titles a user liked/rated highly,
        then recommend the closest titles to that centroid. This is how we generate
        "Because you watched ..." style recommendations for a whole user history,
        not just a single title.
        """
        exclude = exclude or set()
        idxs = [self.movie_id_to_idx[m] for m in liked_movie_ids if m in self.movie_id_to_idx]
        if not idxs:
            return []

        centroid = np.asarray(self._tfidf_matrix[idxs].mean(axis=0))
        sims = cosine_similarity(centroid, self._tfidf_matrix)[0]
        ranked = np.argsort(-sims)

        results = []
        seen = set(liked_movie_ids) | exclude
        for i in ranked:
            mid = int(self.movies_df.iloc[i]["movieId"])
            if mid in seen:
                continue
            results.append((mid, float(sims[i])))
            if len(results) >= top_k:
                break
        return results

    def explain_similarity(self, movie_id_a: int, movie_id_b: int) -> str:
        """Human-readable reason two titles were matched (for Explainable AI feature)."""
        row_a = self.movies_df.loc[self.movies_df.movieId == movie_id_a]
        row_b = self.movies_df.loc[self.movies_df.movieId == movie_id_b]
        if row_a.empty or row_b.empty:
            return "Similar content profile."

        genres_a = set(row_a.iloc[0]["genres"].split("|"))
        genres_b = set(row_b.iloc[0]["genres"].split("|"))
        shared_genres = genres_a & genres_b

        if shared_genres:
            return f"Because it shares the genre(s): {', '.join(sorted(shared_genres))}."
        if row_a.iloc[0]["director"] == row_b.iloc[0]["director"]:
            return f"Because it's directed by {row_a.iloc[0]['director']}, like a title you watched."
        return "Recommended based on similar themes and style."
