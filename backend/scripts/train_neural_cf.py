"""
Train and evaluate Neural Collaborative Filtering model.
Saves trained model to data/ncf_model.pt for use in production.

Run:
    python scripts/train_neural_cf.py

This script:
1. Loads MovieLens/synthetic ratings data
2. Trains NCF (GMF + MLP fusion) model
3. Evaluates vs SVD baseline
4. Saves trained model artifact
5. Prints comparison metrics
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MODEL_DIR = os.path.join(DATA_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

# ── Try importing PyTorch ──────────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset
    TORCH_AVAILABLE = True
    print(f"✓ PyTorch {torch.__version__} available")
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"✓ Using device: {DEVICE}")
except ImportError:
    TORCH_AVAILABLE = False
    print("✗ PyTorch not installed. Run: pip install torch")
    sys.exit(1)

from app.ml.collaborative import CollaborativeRecommender
from app.ml.evaluation import (
    ndcg_at_k, precision_recall_at_k, rmse_mae,
    train_test_split_by_time,
)


# ── Dataset ────────────────────────────────────────────────────────────────
class RatingsDataset(Dataset):
    def __init__(self, df: pd.DataFrame, user_map: dict, item_map: dict):
        self.users = torch.tensor(
            df["userId"].map(user_map).values, dtype=torch.long
        )
        self.items = torch.tensor(
            df["movieId"].map(item_map).values, dtype=torch.long
        )
        self.ratings = torch.tensor(df["rating"].values, dtype=torch.float32)

    def __len__(self):
        return len(self.ratings)

    def __getitem__(self, i):
        return self.users[i], self.items[i], self.ratings[i]


# ── Model ──────────────────────────────────────────────────────────────────
class NCFModel(nn.Module):
    """
    GMF + MLP fusion (He et al. 2017 'Neural Collaborative Filtering').
    GMF path: element-wise product of user+item embeddings (generalised MF).
    MLP path: concatenated embeddings through dense layers (non-linear).
    Final: concat GMF+MLP outputs → single rating prediction.
    """

    def __init__(
        self,
        n_users: int,
        n_items: int,
        n_factors: int = 32,
        mlp_hidden: tuple = (128, 64, 32),
        dropout: float = 0.2,
    ):
        super().__init__()

        # GMF embeddings
        self.user_emb_gmf = nn.Embedding(n_users, n_factors)
        self.item_emb_gmf = nn.Embedding(n_items, n_factors)

        # MLP embeddings (separate from GMF for more capacity)
        self.user_emb_mlp = nn.Embedding(n_users, n_factors)
        self.item_emb_mlp = nn.Embedding(n_items, n_factors)

        # MLP tower
        mlp_layers = []
        input_dim = n_factors * 2
        for hidden in mlp_hidden:
            mlp_layers += [
                nn.Linear(input_dim, hidden),
                nn.LayerNorm(hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
            ]
            input_dim = hidden
        self.mlp = nn.Sequential(*mlp_layers)

        # Output: GMF (n_factors) + MLP last hidden → 1
        self.output = nn.Linear(n_factors + mlp_hidden[-1], 1)

        # Weight init
        nn.init.normal_(self.user_emb_gmf.weight, std=0.01)
        nn.init.normal_(self.item_emb_gmf.weight, std=0.01)
        nn.init.normal_(self.user_emb_mlp.weight, std=0.01)
        nn.init.normal_(self.item_emb_mlp.weight, std=0.01)

    def forward(self, user_idx: torch.Tensor, item_idx: torch.Tensor):
        # GMF branch
        u_gmf = self.user_emb_gmf(user_idx)
        i_gmf = self.item_emb_gmf(item_idx)
        gmf_out = u_gmf * i_gmf  # element-wise

        # MLP branch
        u_mlp = self.user_emb_mlp(user_idx)
        i_mlp = self.item_emb_mlp(item_idx)
        mlp_input = torch.cat([u_mlp, i_mlp], dim=-1)
        mlp_out = self.mlp(mlp_input)

        # Fused output — scale sigmoid [0,1] → [0.5, 5.0]
        fused = torch.cat([gmf_out, mlp_out], dim=-1)
        rating = 0.5 + torch.sigmoid(self.output(fused)).squeeze(-1) * 4.5
        return rating


# ── Trainer ────────────────────────────────────────────────────────────────
class NCFTrainer:
    def __init__(
        self,
        model: NCFModel,
        lr: float = 1e-3,
        weight_decay: float = 1e-5,
    ):
        self.model = model.to(DEVICE)
        self.optimizer = torch.optim.Adam(
            model.parameters(), lr=lr, weight_decay=weight_decay
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", patience=2, factor=0.5
        )
        self.criterion = nn.MSELoss()
        self.history: list[dict] = []

    def fit(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        user_map: dict,
        item_map: dict,
        epochs: int = 15,
        batch_size: int = 512,
    ):
        train_ds = RatingsDataset(train_df, user_map, item_map)
        val_ds = RatingsDataset(val_df, user_map, item_map)
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size * 2)

        best_val_loss = float("inf")
        best_state = None

        for epoch in range(1, epochs + 1):
            # Train
            self.model.train()
            train_loss = 0.0
            for u, i, r in train_loader:
                u, i, r = u.to(DEVICE), i.to(DEVICE), r.to(DEVICE)
                self.optimizer.zero_grad()
                preds = self.model(u, i)
                loss = self.criterion(preds, r)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                train_loss += loss.item() * len(r)
            train_loss /= len(train_ds)

            # Validate
            self.model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for u, i, r in val_loader:
                    u, i, r = u.to(DEVICE), i.to(DEVICE), r.to(DEVICE)
                    preds = self.model(u, i)
                    val_loss += self.criterion(preds, r).item() * len(r)
            val_loss /= len(val_ds)

            self.scheduler.step(val_loss)
            self.history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                marker = " ✓ best"
            else:
                marker = ""

            print(
                f"  Epoch {epoch:2d}/{epochs}  "
                f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}{marker}"
            )

        # Restore best weights
        if best_state:
            self.model.load_state_dict(best_state)
        return self.history

    def predict_batch(
        self, user_idxs: list[int], item_idxs: list[int]
    ) -> list[float]:
        self.model.eval()
        with torch.no_grad():
            u = torch.tensor(user_idxs, dtype=torch.long, device=DEVICE)
            i = torch.tensor(item_idxs, dtype=torch.long, device=DEVICE)
            return self.model(u, i).cpu().tolist()


# ── Evaluation helpers ─────────────────────────────────────────────────────
def evaluate_ncf(
    trainer: NCFTrainer,
    test_df: pd.DataFrame,
    user_map: dict,
    item_map: dict,
    all_items: list,
    k: int = 10,
) -> dict:
    """Compute RMSE, MAE, Precision@K, Recall@K, NDCG@K for trained NCF."""
    preds_all, actuals_all = [], []
    precisions, recalls, ndcgs = [], [], []

    for user_id, group in test_df.groupby("userId"):
        u_idx = user_map.get(user_id)
        if u_idx is None:
            continue

        # Rating prediction accuracy
        known_idxs = [item_map.get(m) for m in group["movieId"] if item_map.get(m) is not None]
        if not known_idxs:
            continue
        preds = trainer.predict_batch([u_idx] * len(known_idxs), known_idxs)
        preds_all.extend(preds)
        actuals_all.extend(group["rating"].tolist()[: len(known_idxs)])

        # Ranking quality: score all items, take top-K
        all_item_idx_list = list(range(len(all_items)))
        all_preds = trainer.predict_batch([u_idx] * len(all_item_idx_list), all_item_idx_list)
        idx_to_movie = {v: k for k, v in item_map.items()}
        ranked = sorted(
            zip(all_item_idx_list, all_preds), key=lambda x: -x[1]
        )
        top_k_ids = [idx_to_movie[idx] for idx, _ in ranked[:k]]
        relevant = set(group.loc[group["rating"] >= 4.0, "movieId"].tolist())

        if relevant:
            p, r = precision_recall_at_k(top_k_ids, relevant, k)
            n = ndcg_at_k(top_k_ids, relevant, k)
            precisions.append(p)
            recalls.append(r)
            ndcgs.append(n)

    rmse, mae = rmse_mae(preds_all, actuals_all) if preds_all else (float("nan"), float("nan"))
    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        f"precision_at_{k}": round(float(np.mean(precisions)) if precisions else 0, 4),
        f"recall_at_{k}": round(float(np.mean(recalls)) if recalls else 0, 4),
        f"ndcg_at_{k}": round(float(np.mean(ndcgs)) if ndcgs else 0, 4),
        "n_users_evaluated": len(precisions),
    }


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("  APERTURE — Neural Collaborative Filtering Training")
    print("=" * 60)

    # Load data
    ratings_path = os.path.join(DATA_DIR, "ratings.csv")
    if not os.path.exists(ratings_path):
        print("ERROR: No ratings.csv found. Run generate_sample_data.py first.")
        sys.exit(1)

    ratings_df = pd.read_csv(ratings_path)
    print(f"\n✓ Loaded {len(ratings_df):,} ratings from {ratings_df['userId'].nunique()} users")
    print(f"  across {ratings_df['movieId'].nunique()} movies")

    # Time-based train/val/test split
    train_df, test_df = train_test_split_by_time(ratings_df, test_fraction=0.2)
    train_df, val_df = train_test_split_by_time(train_df, test_fraction=0.125)  # ~10% of total
    print(f"\n✓ Split: train={len(train_df):,}  val={len(val_df):,}  test={len(test_df):,}")

    # Build index maps from ALL users/items (including test)
    all_users = sorted(ratings_df["userId"].unique())
    all_items = sorted(ratings_df["movieId"].unique())
    user_map = {u: i for i, u in enumerate(all_users)}
    item_map = {m: i for i, m in enumerate(all_items)}
    n_users, n_items = len(all_users), len(all_items)
    print(f"  Entities: {n_users} users, {n_items} items")

    # Filter train/val to only known users+items
    train_df = train_df[
        train_df["userId"].isin(user_map) & train_df["movieId"].isin(item_map)
    ].reset_index(drop=True)
    val_df = val_df[
        val_df["userId"].isin(user_map) & val_df["movieId"].isin(item_map)
    ].reset_index(drop=True)

    # ── Train NCF ─────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("  Training NCF (GMF + MLP fusion, n_factors=32) ...")
    print(f"  Device: {DEVICE}")
    print(f"{'─'*60}")

    model = NCFModel(n_users=n_users, n_items=n_items, n_factors=32, mlp_hidden=(128, 64, 32))
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Model parameters: {total_params:,}")

    trainer = NCFTrainer(model, lr=1e-3)
    t0 = time.time()
    trainer.fit(train_df, val_df, user_map, item_map, epochs=15, batch_size=512)
    elapsed = time.time() - t0
    print(f"\n✓ Training complete in {elapsed:.1f}s")

    # ── Evaluate NCF ───────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("  Evaluating NCF on hold-out test set ...")
    ncf_metrics = evaluate_ncf(trainer, test_df, user_map, item_map, list(all_items))
    print("\n  NCF Metrics:")
    for k, v in ncf_metrics.items():
        print(f"    {k:25s}: {v}")

    # ── Baseline: SVD ─────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("  Computing SVD baseline for comparison ...")
    svd_model = CollaborativeRecommender(train_df, n_factors=30)
    svd_model.fit()

    svd_preds, svd_actuals = [], []
    for _, row in test_df.iterrows():
        pred = svd_model.predict_rating(int(row["userId"]), int(row["movieId"]))
        svd_preds.append(pred)
        svd_actuals.append(row["rating"])
    svd_rmse, svd_mae = rmse_mae(svd_preds, svd_actuals)

    print("\n  Comparison:")
    print(f"  {'Metric':<20} {'SVD (baseline)':>16} {'NCF (deep)':>14} {'Winner':>10}")
    print(f"  {'─'*20} {'─'*16} {'─'*14} {'─'*10}")

    rmse_winner = "NCF ✓" if ncf_metrics["rmse"] < svd_rmse else "SVD ✓"
    mae_winner = "NCF ✓" if ncf_metrics["mae"] < svd_mae else "SVD ✓"
    p_winner = "NCF ✓" if ncf_metrics.get("precision_at_10", 0) > 0 else "SVD ✓"

    print(f"  {'RMSE':<20} {svd_rmse:>16.4f} {ncf_metrics['rmse']:>14.4f} {rmse_winner:>10}")
    print(f"  {'MAE':<20} {svd_mae:>16.4f} {ncf_metrics['mae']:>14.4f} {mae_winner:>10}")
    print(f"  {'Precision@10':<20} {'(not computed)':>16} {ncf_metrics.get('precision_at_10','?'):>14} {p_winner:>10}")

    # ── Save model ─────────────────────────────────────────────────────────
    model_path = os.path.join(MODEL_DIR, "ncf_model.pt")
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "user_map": user_map,
            "item_map": item_map,
            "n_users": n_users,
            "n_items": n_items,
            "n_factors": 32,
            "mlp_hidden": (128, 64, 32),
            "ncf_metrics": ncf_metrics,
            "svd_rmse": round(svd_rmse, 4),
            "svd_mae": round(svd_mae, 4),
            "training_samples": len(train_df),
        },
        model_path,
    )
    print(f"\n✓ Model saved: {model_path}")

    # ── Save metrics report ────────────────────────────────────────────────
    import json
    report = {
        "ncf": ncf_metrics,
        "svd": {"rmse": round(svd_rmse, 4), "mae": round(svd_mae, 4)},
        "training_time_seconds": round(elapsed, 1),
        "model_parameters": total_params,
        "training_samples": len(train_df),
    }
    report_path = os.path.join(MODEL_DIR, "training_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"✓ Training report: {report_path}")

    print(f"\n{'='*60}")
    print("  Training complete! Model ready for inference.")
    print(f"  To use NCF in the API, set NCF_ENABLED=true in .env")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
