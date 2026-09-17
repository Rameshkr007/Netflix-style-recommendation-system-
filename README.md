# Netflix-Style Hybrid Recommendation Platform



---

## Architecture

```
                         ┌────────────────────────┐
                         │  Next.js Frontend       │
                         │  "Aperture" (frontend/) │
  Browser ──────────────▶│  Hero, rails, search,  │
                         │  mood picker, Taste DNA │
                         │  cards, auth context    │
                         └──────────┬──────────────┘
                                    │ fetch (JWT bearer)
                         ┌──────────▼────────────┐
                         │   FastAPI (app/)       │
                         │                        │
                         │  Auth (JWT, RBAC)      │
                         │  Movies / Ratings      │
                         │  Recommendations       │◀──── Redis (cache)
                         │  Search                │
                         │  AI Chat Assistant     │
                         │  Admin Analytics       │
                         │  WebSocket (live)      │
                         └──────────┬─────────────┘
                                    │
                         ┌──────────▼────────────┐
                         │   ML Layer (app/ml/)   │
                         │                        │
                         │  ContentBasedRecommender│ (TF-IDF + cosine similarity)
                         │  CollaborativeRecommender│ (Truncated SVD matrix factorization)
                         │  HybridRecommender      │ (weighted blend + explainability)
                         │  MoodRecommender        │ (mood→genre NLP mapping)
                         │  SearchService          │ (fuzzy + semantic search)
                         │  evaluation.py          │ (Precision@K, Recall@K, RMSE, MAE, NDCG)
                         │  neural_cf.py (optional)│ (PyTorch NCF, lazy-imported)
                         └──────────┬─────────────┘
                                    │
                         ┌──────────▼────────────┐
                         │     PostgreSQL         │
                         │  users, movies,        │
                         │  ratings, watch_history,│
                         │  search_history,       │
                         │  watchlist_items       │
                         └────────────────────────┘
```



