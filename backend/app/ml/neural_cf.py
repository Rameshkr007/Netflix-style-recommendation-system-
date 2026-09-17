"""
Neural Collaborative Filtering (NCF)
--------------------------------------
A deep learning recommender that learns user and item embeddings jointly
with a multi-layer perceptron, rather than the fixed bilinear form used in
classic matrix factorization. This generally captures more complex,
non-linear interaction patterns once you have enough rating data
(hundreds of thousands+ of interactions).

This module is intentionally optional / lazily imported: PyTorch is a heavy
dependency, and the SVD-based CollaborativeRecommender in collaborative.py
is sufficient for small-to-medium datasets and is what the API uses by
default. Wire this in via app/ml/hybrid.py once you have enough real
interaction data and want the extra modeling capacity.

Usage:
    model = NeuralCFModel(n_users, n_items, n_factors=32)
    trainer = NeuralCFTrainer(model)
    trainer.fit(ratings_df, user_id_to_idx, movie_id_to_idx, epochs=10)
    predicted_rating = trainer.predict(user_id, movie_id)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover - torch is an optional heavy dependency
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:

    class _RatingsDataset(Dataset):
        def __init__(self, user_idx: np.ndarray, item_idx: np.ndarray, ratings: np.ndarray):
            self.user_idx = torch.tensor(user_idx, dtype=torch.long)
            self.item_idx = torch.tensor(item_idx, dtype=torch.long)
            self.ratings = torch.tensor(ratings, dtype=torch.float32)

        def __len__(self):
            return len(self.ratings)

        def __getitem__(self, i):
            return self.user_idx[i], self.item_idx[i], self.ratings[i]

    class NeuralCFModel(nn.Module):
        """
        GMF (Generalized Matrix Factorization) + MLP fused architecture,
        following He et al. 2017 "Neural Collaborative Filtering".
        """

        def __init__(self, n_users: int, n_items: int, n_factors: int = 32,
                     mlp_hidden: tuple[int, ...] = (64, 32, 16)):
            super().__init__()
            self.user_embedding_gmf = nn.Embedding(n_users, n_factors)
            self.item_embedding_gmf = nn.Embedding(n_items, n_factors)
            self.user_embedding_mlp = nn.Embedding(n_users, n_factors)
            self.item_embedding_mlp = nn.Embedding(n_items, n_factors)

            mlp_layers = []
            input_dim = n_factors * 2
            for hidden_dim in mlp_hidden:
                mlp_layers += [nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Dropout(0.2)]
                input_dim = hidden_dim
            self.mlp = nn.Sequential(*mlp_layers)

            self.output_layer = nn.Linear(n_factors + mlp_hidden[-1], 1)
            self.sigmoid = nn.Sigmoid()

        def forward(self, user_idx, item_idx):
            gmf_vec = self.user_embedding_gmf(user_idx) * self.item_embedding_gmf(item_idx)

            mlp_input = torch.cat(
                [self.user_embedding_mlp(user_idx), self.item_embedding_mlp(item_idx)], dim=-1
            )
            mlp_vec = self.mlp(mlp_input)

            combined = torch.cat([gmf_vec, mlp_vec], dim=-1)
            # scale sigmoid output [0,1] -> rating scale [0.5, 5.0]
            return 0.5 + self.sigmoid(self.output_layer(combined)).squeeze(-1) * 4.5

    class NeuralCFTrainer:
        def __init__(self, model: NeuralCFModel, lr: float = 1e-3):
            self.model = model
            self.optimizer = torch.optim.Adam(model.parameters(), lr=lr)
            self.criterion = nn.MSELoss()
            self.user_id_to_idx: dict[int, int] = {}
            self.movie_id_to_idx: dict[int, int] = {}

        def fit(self, ratings_df: pd.DataFrame, epochs: int = 10, batch_size: int = 256):
            user_ids = sorted(ratings_df["userId"].unique())
            movie_ids = sorted(ratings_df["movieId"].unique())
            self.user_id_to_idx = {u: i for i, u in enumerate(user_ids)}
            self.movie_id_to_idx = {m: i for i, m in enumerate(movie_ids)}

            user_idx = ratings_df["userId"].map(self.user_id_to_idx).values
            item_idx = ratings_df["movieId"].map(self.movie_id_to_idx).values
            ratings = ratings_df["rating"].values

            dataset = _RatingsDataset(user_idx, item_idx, ratings)
            loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

            self.model.train()
            history = []
            for epoch in range(epochs):
                total_loss = 0.0
                for u, i, r in loader:
                    self.optimizer.zero_grad()
                    preds = self.model(u, i)
                    loss = self.criterion(preds, r)
                    loss.backward()
                    self.optimizer.step()
                    total_loss += loss.item() * len(r)
                avg_loss = total_loss / len(dataset)
                history.append(avg_loss)
            return history

        def predict(self, user_id: int, movie_id: int) -> float:
            if user_id not in self.user_id_to_idx or movie_id not in self.movie_id_to_idx:
                return 3.0  # fallback: global-ish midpoint for unseen entities
            self.model.eval()
            with torch.no_grad():
                u = torch.tensor([self.user_id_to_idx[user_id]], dtype=torch.long)
                i = torch.tensor([self.movie_id_to_idx[movie_id]], dtype=torch.long)
                return float(self.model(u, i).item())

else:  # pragma: no cover

    class NeuralCFModel:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "PyTorch is not installed. Install it with `pip install torch` "
                "to use the Neural Collaborative Filtering model. The SVD-based "
                "CollaborativeRecommender in collaborative.py works without it."
            )

    class NeuralCFTrainer:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "PyTorch is not installed. Install it with `pip install torch` "
                "to use the Neural Collaborative Filtering model."
            )
