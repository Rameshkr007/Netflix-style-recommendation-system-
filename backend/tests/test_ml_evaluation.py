import pandas as pd

from app.ml.evaluation import (
    ndcg_at_k,
    precision_recall_at_k,
    rmse_mae,
    train_test_split_by_time,
)
from app.ml.hybrid import HybridRecommender


def test_precision_recall_at_k_perfect_match():
    recommended = [1, 2, 3, 4, 5]
    relevant = {1, 2, 3, 4, 5}
    precision, recall = precision_recall_at_k(recommended, relevant, k=5)
    assert precision == 1.0
    assert recall == 1.0


def test_precision_recall_at_k_no_overlap():
    recommended = [1, 2, 3]
    relevant = {7, 8, 9}
    precision, recall = precision_recall_at_k(recommended, relevant, k=3)
    assert precision == 0.0
    assert recall == 0.0


def test_precision_recall_at_k_partial_overlap():
    recommended = [1, 2, 3, 4]
    relevant = {1, 3, 99}
    precision, recall = precision_recall_at_k(recommended, relevant, k=4)
    assert precision == 0.5  # 2 of 4 recommended are relevant
    assert abs(recall - 2 / 3) < 1e-9  # 2 of 3 relevant items were found


def test_ndcg_rewards_higher_ranked_hits():
    relevant = {5}
    ndcg_first = ndcg_at_k([5, 1, 2, 3], relevant, k=4)
    ndcg_last = ndcg_at_k([1, 2, 3, 5], relevant, k=4)
    assert ndcg_first == 1.0  # ideal ranking
    assert ndcg_last < ndcg_first


def test_rmse_mae_zero_error():
    rmse, mae = rmse_mae([3.0, 4.0, 5.0], [3.0, 4.0, 5.0])
    assert rmse == 0.0
    assert mae == 0.0


def test_rmse_mae_known_error():
    rmse, mae = rmse_mae([4.0, 4.0], [3.0, 5.0])
    assert abs(mae - 1.0) < 1e-9
    assert abs(rmse - 1.0) < 1e-9


def test_train_test_split_by_time_keeps_recent_in_test():
    ratings = pd.DataFrame({
        "userId": [1, 1, 1, 1, 1],
        "movieId": [10, 11, 12, 13, 14],
        "rating": [3, 4, 5, 2, 1],
        "timestamp": [100, 200, 300, 400, 500],
    })
    train, test = train_test_split_by_time(ratings, test_fraction=0.4)
    assert len(train) == 3
    assert len(test) == 2
    assert set(test["movieId"]) == {13, 14}  # the two most recent


def test_hybrid_model_fits_and_recommends_on_toy_data():
    movies = pd.DataFrame([
        {"movieId": 1, "title": "A", "genres": "Action", "director": "X", "cast": "P, Q", "synopsis": "fight"},
        {"movieId": 2, "title": "B", "genres": "Action", "director": "X", "cast": "P, R", "synopsis": "battle"},
        {"movieId": 3, "title": "C", "genres": "Romance", "director": "Y", "cast": "S, T", "synopsis": "love"},
        {"movieId": 4, "title": "D", "genres": "Romance", "director": "Y", "cast": "S, U", "synopsis": "romance"},
    ])
    ratings = pd.DataFrame([
        {"userId": 1, "movieId": 1, "rating": 5.0, "timestamp": 1},
        {"userId": 1, "movieId": 2, "rating": 4.5, "timestamp": 2},
        {"userId": 2, "movieId": 3, "rating": 5.0, "timestamp": 1},
        {"userId": 2, "movieId": 4, "rating": 4.0, "timestamp": 2},
        {"userId": 3, "movieId": 1, "rating": 5.0, "timestamp": 1},
    ])
    model = HybridRecommender(movies, ratings).fit()
    recs = model.recommend(user_id=1, top_k=2)
    assert len(recs) > 0
    # user 1 liked Action -> should not get titles they already rated
    rec_ids = {r.movie_id for r in recs}
    assert 1 not in rec_ids and 2 not in rec_ids

    cold_recs = model.recommend(user_id=999, top_k=2)
    assert all(r.source == "popularity" for r in cold_recs)
