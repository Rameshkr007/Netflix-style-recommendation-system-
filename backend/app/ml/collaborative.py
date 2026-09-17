"""
Collaborative Filtering Recommendation Engine
-----------------------------------------------
Implements matrix factorization via Truncated SVD over the sparse
user-item rating matrix. This captures "users similar to you also liked Y"
patterns that pure content similarity cannot see (e.g. two visually/
thematically unrelated titles that the same taste-cluster of users enjoys).

For production-scale data, this same interface can be swapped for the
`surprise` library's SVD / SVD++ or a neural CF model (see neural_cf.py)
without changing the calling code in hybrid.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD


class CollaborativeRecommender:
    def __init__(self, ratings_df: pd.DataFrame, n_factors: int = 30):
        self.ratings_df = ratings_df
        self.n_factors = n_factors

        self.user_ids = [int(u) for u in sorted(ratings_df["userId"].unique())]
        self.movie_ids = [int(m) for m in sorted(ratings_df["movieId"].unique())]
        self.user_id_to_idx = {u: i for i, u in enumerate(self.user_ids)}
        self.movie_id_to_idx = {m: i for i, m in enumerate(self.movie_ids)}
        self.idx_to_movie_id = {i: m for m, i in self.movie_id_to_idx.items()}

        self.global_mean = ratings_df["rating"].mean()
        self._user_factors: np.ndarray | None = None
        self._item_factors: np.ndarray | None = None
        self._user_means: dict[int, float] = {}

    def _build_matrix(self) -> csr_matrix:
        n_users, n_items = len(self.user_ids), len(self.movie_ids)
        rows = self.ratings_df["userId"].map(self.user_id_to_idx)
        cols = self.ratings_df["movieId"].map(self.movie_id_to_idx)

        # mean-center each user's ratings so SVD models *preference deviation*,
        # not just "users who rate everything 5 stars" -> avoids popularity bias
        user_means = self.ratings_df.groupby("userId")["rating"].mean()
        self._user_means = user_means.to_dict()
        centered = self.ratings_df["rating"].values - self.ratings_df["userId"].map(user_means).values

        return csr_matrix((centered, (rows, cols)), shape=(n_users, n_items))

    def fit(self) -> "CollaborativeRecommender":
        matrix = self._build_matrix()
        n_factors = min(self.n_factors, min(matrix.shape) - 1)
        svd = TruncatedSVD(n_components=max(n_factors, 2), random_state=42)
        self._user_factors = svd.fit_transform(matrix)
        self._item_factors = svd.components_.T
        return self

    def predict_rating(self, user_id: int, movie_id: int) -> float:
        """Predict what rating a user would give a movie."""
        if user_id not in self.user_id_to_idx or movie_id not in self.movie_id_to_idx:
            return self.global_mean

        u_idx = self.user_id_to_idx[user_id]
        m_idx = self.movie_id_to_idx[movie_id]
        deviation = float(np.dot(self._user_factors[u_idx], self._item_factors[m_idx]))
        baseline = self._user_means.get(user_id, self.global_mean)
        return float(np.clip(baseline + deviation, 0.5, 5.0))

    def recommend_for_user(
        self, user_id: int, top_k: int = 10, exclude: set[int] | None = None
    ) -> list[tuple[int, float]]:
        """Return [(movieId, predicted_rating), ...] ranked highest first."""
        exclude = set(exclude or set())
        if user_id in self.user_id_to_idx:
            already_rated = set(
                self.ratings_df.loc[self.ratings_df.userId == user_id, "movieId"]
            )
            exclude |= already_rated

        candidates = [m for m in self.movie_ids if m not in exclude]
        if not candidates:
            return []

        preds = [(m, self.predict_rating(user_id, m)) for m in candidates]
        preds.sort(key=lambda x: -x[1])
        return preds[:top_k]

    def is_known_user(self, user_id: int) -> bool:
        return user_id in self.user_id_to_idx
