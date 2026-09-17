"""
Recommendation Quality Evaluation
------------------------------------
Implements the standard offline evaluation metrics for recommender systems:

  - RMSE / MAE        : rating-prediction accuracy (regression-style)
  - Precision@K       : of the K items we recommended, what fraction were relevant?
  - Recall@K          : of all relevant items, what fraction did we surface in top K?
  - NDCG@K            : like Precision@K but rewards relevant items ranked higher

"Relevant" = the user actually rated that item >= RELEVANCE_THRESHOLD in the
held-out test set. This file also provides a simple time-based train/test
split and an `evaluate_hybrid_model` runner that ties it all together, plus
a minimal A/B test comparator for two candidate models/configs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

RELEVANCE_THRESHOLD = 4.0


@dataclass
class EvalResult:
    rmse: float
    mae: float
    precision_at_k: float
    recall_at_k: float
    ndcg_at_k: float
    k: int
    n_users_evaluated: int
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "rmse": round(self.rmse, 4),
            "mae": round(self.mae, 4),
            f"precision_at_{self.k}": round(self.precision_at_k, 4),
            f"recall_at_{self.k}": round(self.recall_at_k, 4),
            f"ndcg_at_{self.k}": round(self.ndcg_at_k, 4),
            "n_users_evaluated": self.n_users_evaluated,
        }


def train_test_split_by_time(ratings_df: pd.DataFrame, test_fraction: float = 0.2):
    """
    Per-user time-based split: each user's most-recent test_fraction of
    ratings goes to the test set. This is more realistic than a random split
    because it mimics actually predicting *future* behavior, not interpolating
    inside a user's known history.
    """
    train_rows, test_rows = [], []
    for _, group in ratings_df.groupby("userId"):
        group = group.sort_values("timestamp")
        n_test = max(1, int(len(group) * test_fraction))
        if len(group) <= n_test:
            train_rows.append(group)
            continue
        train_rows.append(group.iloc[:-n_test])
        test_rows.append(group.iloc[-n_test:])

    train_df = pd.concat(train_rows).reset_index(drop=True) if train_rows else ratings_df.iloc[0:0]
    test_df = pd.concat(test_rows).reset_index(drop=True) if test_rows else ratings_df.iloc[0:0]
    return train_df, test_df


def rmse_mae(predicted: list[float], actual: list[float]) -> tuple[float, float]:
    predicted_arr = np.array(predicted)
    actual_arr = np.array(actual)
    rmse = float(np.sqrt(np.mean((predicted_arr - actual_arr) ** 2)))
    mae = float(np.mean(np.abs(predicted_arr - actual_arr)))
    return rmse, mae


def precision_recall_at_k(
    recommended_ids: list[int], relevant_ids: set[int], k: int
) -> tuple[float, float]:
    top_k = recommended_ids[:k]
    if not top_k:
        return 0.0, 0.0
    hits = len(set(top_k) & relevant_ids)
    precision = hits / len(top_k)
    recall = hits / len(relevant_ids) if relevant_ids else 0.0
    return precision, recall


def ndcg_at_k(recommended_ids: list[int], relevant_ids: set[int], k: int) -> float:
    top_k = recommended_ids[:k]
    dcg = sum(
        1.0 / math.log2(i + 2) for i, mid in enumerate(top_k) if mid in relevant_ids
    )
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_hybrid_model(hybrid_model, test_df: pd.DataFrame, k: int = 10) -> EvalResult:
    """
    Runs the full offline evaluation suite for a fitted HybridRecommender
    against a held-out test set of (user, movie, rating) triples.
    """
    from app.ml.hybrid import HybridRecommender  # local import avoids circulars

    assert isinstance(hybrid_model, HybridRecommender)

    rmse_preds, rmse_actuals = [], []
    precisions, recalls, ndcgs = [], [], []
    n_evaluated = 0

    for user_id, group in test_df.groupby("userId"):
        relevant_ids = set(group.loc[group.rating >= RELEVANCE_THRESHOLD, "movieId"])

        # rating-prediction accuracy via the collaborative model's predict_rating
        for _, row in group.iterrows():
            pred = hybrid_model.collab_model.predict_rating(user_id, row["movieId"])
            rmse_preds.append(pred)
            rmse_actuals.append(row["rating"])

        if not relevant_ids:
            continue

        recs = hybrid_model.recommend(user_id, top_k=k)
        recommended_ids = [r.movie_id for r in recs]

        p, r = precision_recall_at_k(recommended_ids, relevant_ids, k)
        ndcg = ndcg_at_k(recommended_ids, relevant_ids, k)
        precisions.append(p)
        recalls.append(r)
        ndcgs.append(ndcg)
        n_evaluated += 1

    rmse, mae = rmse_mae(rmse_preds, rmse_actuals) if rmse_preds else (float("nan"), float("nan"))

    return EvalResult(
        rmse=rmse,
        mae=mae,
        precision_at_k=float(np.mean(precisions)) if precisions else 0.0,
        recall_at_k=float(np.mean(recalls)) if recalls else 0.0,
        ndcg_at_k=float(np.mean(ndcgs)) if ndcgs else 0.0,
        k=k,
        n_users_evaluated=n_evaluated,
    )


def ab_test_compare(result_a: EvalResult, result_b: EvalResult, label_a="A", label_b="B") -> dict:
    """
    Minimal A/B comparator: reports the relative lift of model B over model A
    across each metric, for deciding whether a new model/config (e.g. a
    different alpha blend weight) is actually an improvement.
    """

    def lift(a, b):
        if a == 0:
            return float("inf") if b > 0 else 0.0
        return (b - a) / a * 100

    return {
        label_a: result_a.as_dict(),
        label_b: result_b.as_dict(),
        "lift_percent": {
            "precision_at_k": round(lift(result_a.precision_at_k, result_b.precision_at_k), 2),
            "recall_at_k": round(lift(result_a.recall_at_k, result_b.recall_at_k), 2),
            "ndcg_at_k": round(lift(result_a.ndcg_at_k, result_b.ndcg_at_k), 2),
            "rmse": round(lift(result_a.rmse, result_b.rmse), 2),
        },
    }
