"""
NCF Inference Wrapper
-----------------------
Loads the trained NCF model from disk for production inference.
Used by HybridRecommender when NCF_ENABLED=true in settings.

This keeps inference completely separate from training —
training happens in scripts/train_neural_cf.py (scheduled nightly),
inference happens here on every recommendation request.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.info("PyTorch not available — NCF inference disabled")


class NCFInference:
    """
    Loads a saved NCF model checkpoint and provides fast rating predictions.
    Falls back to None gracefully if PyTorch/checkpoint not available.
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None
        self._user_map: dict[int, int] = {}
        self._item_map: dict[int, int] = {}
        self._loaded = False
        self._load()

    def _load(self) -> None:
        if not TORCH_AVAILABLE:
            return
        if not os.path.exists(self.model_path):
            logger.warning("NCF model not found at %s — run train_neural_cf.py first", self.model_path)
            return

        try:
            from scripts.train_neural_cf import NCFModel  # import the class
            checkpoint = torch.load(self.model_path, map_location="cpu", weights_only=False)

            self._user_map = checkpoint["user_map"]
            self._item_map = checkpoint["item_map"]

            model = NCFModel(
                n_users=checkpoint["n_users"],
                n_items=checkpoint["n_items"],
                n_factors=checkpoint["n_factors"],
                mlp_hidden=checkpoint["mlp_hidden"],
            )
            model.load_state_dict(checkpoint["model_state_dict"])
            model.eval()
            self._model = model
            self._loaded = True

            metrics = checkpoint.get("ncf_metrics", {})
            logger.info(
                "NCF model loaded: RMSE=%.4f vs SVD RMSE=%.4f",
                metrics.get("rmse", 0),
                checkpoint.get("svd_rmse", 0),
            )
        except Exception as e:
            logger.error("Failed to load NCF model: %s", e)

    @property
    def is_available(self) -> bool:
        return self._loaded and self._model is not None

    def predict_rating(self, user_id: int, movie_id: int) -> Optional[float]:
        """Predict rating for a user-movie pair. Returns None if not available."""
        if not self.is_available:
            return None
        u_idx = self._user_map.get(user_id)
        m_idx = self._item_map.get(movie_id)
        if u_idx is None or m_idx is None:
            return None
        try:
            with torch.no_grad():
                u = torch.tensor([u_idx], dtype=torch.long)
                i = torch.tensor([m_idx], dtype=torch.long)
                return float(self._model(u, i).item())
        except Exception as e:
            logger.warning("NCF predict failed: %s", e)
            return None

    def predict_batch(
        self, user_id: int, movie_ids: list[int]
    ) -> dict[int, float]:
        """Predict ratings for multiple movies for one user."""
        if not self.is_available:
            return {}
        u_idx = self._user_map.get(user_id)
        if u_idx is None:
            return {}

        results = {}
        valid_pairs = [
            (mid, self._item_map[mid])
            for mid in movie_ids
            if mid in self._item_map
        ]
        if not valid_pairs:
            return {}

        try:
            with torch.no_grad():
                mids, m_idxs = zip(*valid_pairs)
                u_tensor = torch.tensor([u_idx] * len(m_idxs), dtype=torch.long)
                i_tensor = torch.tensor(list(m_idxs), dtype=torch.long)
                preds = self._model(u_tensor, i_tensor).tolist()
                for mid, pred in zip(mids, preds):
                    results[int(mid)] = float(pred)
        except Exception as e:
            logger.warning("NCF batch predict failed: %s", e)
        return results


# Singleton — loaded once at startup
_ncf_instance: Optional[NCFInference] = None


def get_ncf_inference() -> Optional[NCFInference]:
    """Get the singleton NCF inference instance."""
    global _ncf_instance
    if _ncf_instance is None:
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "models", "ncf_model.pt"
        )
        _ncf_instance = NCFInference(os.path.abspath(model_path))
    return _ncf_instance if _ncf_instance.is_available else None
