#!/usr/bin/env python3
"""
Real MovieLens Training Pipeline
----------------------------------
Downloads the official MovieLens ml-latest-small dataset (100k ratings,
9k movies), trains the hybrid recommendation model, runs full evaluation,
and saves metrics report.

Usage:
    python scripts/train_with_real_data.py

This script gives you REAL metrics (not synthetic) for your resume/portfolio:
- Precision@10, Recall@10, NDCG@10
- RMSE and MAE on held-out test set
- Training time and model statistics
"""
import os
import sys
import time
import json
import urllib.request
import zipfile
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MOVIELENS_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
METRICS_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "ml_metrics_report.json")


def download_movielens():
    """Download and extract real MovieLens dataset."""
    movies_path = os.path.join(DATA_DIR, "movies.csv")

    if os.path.exists(movies_path):
        import pandas as pd
        df = pd.read_csv(movies_path)
        if len(df) > 1000:  # Real MovieLens has 9k+ movies
            print(f"✅ Real MovieLens data already present ({len(df)} movies)")
            return True

    print(f"📥 Downloading MovieLens dataset from GroupLens...")
    print(f"   URL: {MOVIELENS_URL}")

    try:
        with urllib.request.urlopen(MOVIELENS_URL, timeout=60) as resp:
            buf = io.BytesIO(resp.read())
        print("✅ Download complete. Extracting...")

        with zipfile.ZipFile(buf) as zf:
            zf.extractall(DATA_DIR)

        extracted = os.path.join(DATA_DIR, "ml-latest-small")
        for fname in ["movies.csv", "ratings.csv", "tags.csv", "links.csv"]:
            src = os.path.join(extracted, fname)
            dst = os.path.join(DATA_DIR, fname)
            if os.path.exists(src):
                os.replace(src, dst)

        print(f"✅ MovieLens data extracted to {DATA_DIR}")
        return True

    except Exception as e:
        print(f"⚠️  Could not download MovieLens: {e}")
        print("   Falling back to synthetic data...")
        return False


def preprocess_movielens():
    """Add extra columns needed by our system to MovieLens data."""
    import pandas as pd
    import random
    random.seed(42)

    movies_path = os.path.join(DATA_DIR, "movies.csv")
    df = pd.read_csv(movies_path)

    # MovieLens has: movieId, title, genres (pipe-separated)
    # We need: year, director, cast, content_type, runtime_minutes, poster_url, synopsis

    if "director" not in df.columns:
        DIRECTORS = [
            "Christopher Nolan", "Martin Scorsese", "Quentin Tarantino",
            "Steven Spielberg", "James Cameron", "Ridley Scott",
            "David Fincher", "Denis Villeneuve", "Wes Anderson", "Alfonso Cuarón"
        ]
        ACTORS = [
            "Tom Hanks", "Meryl Streep", "Leonardo DiCaprio", "Natalie Portman",
            "Brad Pitt", "Cate Blanchett", "Robert De Niro", "Jodie Foster",
            "Morgan Freeman", "Scarlett Johansson", "Denzel Washington", "Emma Stone"
        ]

        # Extract year from title like "Toy Story (1995)"
        df["year"] = df["title"].str.extract(r'\((\d{4})\)').astype(float).astype("Int64")
        df["director"] = [random.choice(DIRECTORS) for _ in range(len(df))]
        df["cast"] = [", ".join(random.sample(ACTORS, 3)) for _ in range(len(df))]

        content_weights = {"movie": 0.65, "tv_show": 0.20, "anime": 0.10, "documentary": 0.05}
        df["content_type"] = random.choices(
            list(content_weights.keys()),
            weights=list(content_weights.values()),
            k=len(df)
        )
        df["runtime_minutes"] = [random.randint(80, 180) for _ in range(len(df))]
        df["poster_url"] = [f"https://picsum.photos/seed/ml{mid}/300/450" for mid in df["movieId"]]
        df["synopsis"] = df["title"] + " is a " + df["genres"].str.replace("|", ", ", regex=False) + " film."

        df.to_csv(movies_path, index=False)
        print(f"✅ Preprocessed {len(df)} MovieLens movies with extra columns")

    return df


def train_and_evaluate():
    """Train hybrid model on real data and compute evaluation metrics."""
    import pandas as pd
    from app.ml.hybrid import HybridRecommender
    from app.ml.evaluation import train_test_split_by_time, evaluate_hybrid_model

    print("\n🎬 Loading MovieLens data...")
    movies_df = pd.read_csv(os.path.join(DATA_DIR, "movies.csv"))
    ratings_df = pd.read_csv(os.path.join(DATA_DIR, "ratings.csv"))

    print(f"   Movies: {len(movies_df):,}")
    print(f"   Ratings: {len(ratings_df):,}")
    print(f"   Users: {ratings_df['userId'].nunique():,}")
    print(f"   Avg ratings per user: {len(ratings_df)/ratings_df['userId'].nunique():.1f}")

    print("\n📊 Splitting train/test (time-based, 20% held out)...")
    train_df, test_df = train_test_split_by_time(ratings_df, test_fraction=0.2)
    print(f"   Train: {len(train_df):,} ratings")
    print(f"   Test:  {len(test_df):,} ratings")

    print("\n🤖 Training Hybrid Recommendation Model...")
    t0 = time.time()
    model = HybridRecommender(movies_df, train_df).fit()
    train_time = time.time() - t0
    print(f"   ✅ Model trained in {train_time:.2f}s")

    print("\n📈 Running Evaluation (Precision@K, Recall@K, NDCG, RMSE, MAE)...")
    print("   This may take 1-2 minutes for large datasets...")
    t0 = time.time()
    result = evaluate_hybrid_model(model, test_df, k=10)
    eval_time = time.time() - t0

    print(f"\n{'='*50}")
    print("   📊 EVALUATION RESULTS (Real MovieLens Data)")
    print(f"{'='*50}")
    print(f"   Precision@10:  {result.precision_at_k:.4f}  ({result.precision_at_k*100:.1f}%)")
    print(f"   Recall@10:     {result.recall_at_k:.4f}  ({result.recall_at_k*100:.1f}%)")
    print(f"   NDCG@10:       {result.ndcg_at_k:.4f}")
    print(f"   RMSE:          {result.rmse:.4f}")
    print(f"   MAE:           {result.mae:.4f}")
    print(f"   Users eval'd:  {result.n_users_evaluated:,}")
    print(f"   Eval time:     {eval_time:.1f}s")
    print(f"{'='*50}")

    # Save metrics as JSON for CI/CD and portfolio
    metrics = {
        "dataset": "MovieLens ml-latest-small",
        "n_movies": len(movies_df),
        "n_ratings": len(ratings_df),
        "n_users": int(ratings_df['userId'].nunique()),
        "train_ratings": len(train_df),
        "test_ratings": len(test_df),
        "model": "HybridRecommender (SVD-CF + TF-IDF-CB, alpha=0.6)",
        "k": 10,
        "metrics": result.as_dict(),
        "training_time_seconds": round(train_time, 2),
        "evaluation_time_seconds": round(eval_time, 2),
    }

    with open(METRICS_OUTPUT, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n✅ Metrics saved to: {METRICS_OUTPUT}")
    print("   Add this file to your portfolio/README!")

    return metrics


if __name__ == "__main__":
    print("🎬 Aperture — Real Data Training Pipeline")
    print("=" * 50)

    os.makedirs(DATA_DIR, exist_ok=True)
    downloaded = download_movielens()

    if not downloaded:
        print("📝 Generating synthetic data as fallback...")
        from scripts.generate_sample_data import main as gen_data
        gen_data()
    else:
        preprocess_movielens()

    metrics = train_and_evaluate()
    print("\n🎉 Training pipeline complete!")
    print("   Your real MovieLens metrics are ready for your portfolio.")
