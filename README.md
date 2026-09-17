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
Running locally without Docker
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# point at a local Postgres + Redis, or use SQLite for quick local testing:
export DATABASE_URL="sqlite:///./local.db"
export REDIS_URL="redis://localhost:6379/0"   # optional -- the app fails open if Redis is down

python scripts/generate_sample_data.py   # if data/ doesn't already exist
python scripts/seed_database.py
uvicorn app.main:app --reload
In a second terminal, run the frontend:

cd frontend
npm install
cp .env.local.example .env.local   # defaults to http://localhost:8000/api/v1
npm run dev
Visit http://localhost:3000.

Running tests
cd backend
pip install -r requirements.txt
pytest -v


