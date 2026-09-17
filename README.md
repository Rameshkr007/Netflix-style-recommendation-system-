# Netflix-Style Hybrid Recommendation Platform

A working, tested full-stack application for an AI-powered streaming
recommendation platform: **FastAPI + PostgreSQL + Redis** backend with a
**hybrid recommendation engine** (content-based filtering + collaborative
filtering via matrix factorization), mood-based NLP recommendations,
semantic/fuzzy search, an AI chat assistant, real-time trending, and an admin
analytics dashboard backend — plus a **Next.js + Tailwind + Framer Motion**
frontend ("Aperture") with glassmorphism UI, 3D hover cards, a particle-field
hero, skeleton loading, and a Taste DNA visualization.

This is the **working foundation** of the larger system described in the
original spec (which also calls for deep learning models in production,
cloud deployment, webcam emotion detection, friend-matching, etc.).
Everything in this repo is real, runnable code — not a mockup. See
[What's intentionally not included yet](#whats-intentionally-not-included-yet)
for an honest list of what's left.

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

### How recommendations actually work

1. **Content-Based Filtering** (`app/ml/content_based.py`): builds a TF-IDF
   vector per title from genres + director + cast + synopsis, then recommends
   by cosine similarity. Works even for brand-new users/titles (no cold-start
   problem).
2. **Collaborative Filtering** (`app/ml/collaborative.py`): mean-centers the
   user-item rating matrix and factorizes it with Truncated SVD, capturing
   "users like you also liked Y" patterns content similarity can't see.
3. **Hybrid blend** (`app/ml/hybrid.py`): `score = alpha * CF_score + (1-alpha) * CB_score`,
   default `alpha=0.6`. Falls back gracefully: a user with zero ratings gets
   Bayesian-weighted popularity rankings; a user who just rated a few titles
   gets immediate content-based blending (via live DB reads) even before the
   next full model refit.
4. **Explainability**: every recommendation carries a human-readable `reason`
   string ("Because you watched X, and viewers with similar taste also rated
   this highly.").
5. The model is refit periodically (`POST /api/v1/admin/model/refresh`), not
   on every request — refitting TF-IDF/SVD per API call would be far too slow.
   In production, wire this to a cron job / Celery beat task.

---

## Quickstart (Docker Compose)

```bash
git clone <this repo>
cd netflix-rec-system
cp .env.example .env
# edit .env and set a real JWT_SECRET_KEY: openssl rand -hex 32

docker compose up --build
```

This starts Postgres, Redis, the API on `http://localhost:8000`, and the
Next.js frontend on `http://localhost:3000`.

Then seed the database with the sample catalog + ratings:

```bash
docker compose exec api python scripts/seed_database.py
```

Open `http://localhost:3000` for the app, `http://localhost:8000/docs` for
interactive Swagger docs covering every endpoint, or `http://localhost:8000/redoc`
for ReDoc.

Two accounts are created by the seed script:

| email | password | role |
|---|---|---|
| `admin@example.com` | `Admin1234!` | admin |
| `demo@example.com` | `Demo1234!` | user |

### Using real MovieLens data instead of synthetic sample data

By default, `scripts/generate_sample_data.py` has already produced a
realistic 400-title / 10k-rating synthetic catalog in `backend/data/` so the
system works out of the box with zero setup. To use the real, public
MovieLens dataset instead:

```bash
cd backend
python scripts/download_movielens.py     # downloads ml-latest-small (~1MB, 100k ratings)
python scripts/seed_database.py          # re-seed (delete existing rows first if re-seeding)
```

> Note: the real MovieLens schema doesn't include `director`/`cast`/
> `poster_url`/`content_type` columns the way the synthetic generator's does.
> If you swap in real MovieLens data, either enrich it with TMDB/OMDB data
> first, or relax `seed_database.py`'s expectations accordingly.

---

## Running locally without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# point at a local Postgres + Redis, or use SQLite for quick local testing:
export DATABASE_URL="sqlite:///./local.db"
export REDIS_URL="redis://localhost:6379/0"   # optional -- the app fails open if Redis is down

python scripts/generate_sample_data.py   # if data/ doesn't already exist
python scripts/seed_database.py
uvicorn app.main:app --reload
```

In a second terminal, run the frontend:

```bash
cd frontend
npm install
cp .env.local.example .env.local   # defaults to http://localhost:8000/api/v1
npm run dev
```

Visit `http://localhost:3000`.

---

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

31 tests covering auth/JWT/RBAC, movie CRUD, ratings, watchlist, the full
recommendation pipeline (cold-start, hybrid, mood-based, trending, taste DNA),
and ML evaluation metrics in isolation (Precision@K, Recall@K, NDCG, RMSE,
MAE, train/test splitting). Each test runs against its own throwaway SQLite
file — no shared state, no need for Postgres/Redis to be running.

---

## API Reference (selected)

All endpoints are under `/api/v1` unless noted. Full interactive docs at `/docs`.

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create account, returns JWT |
| POST | `/auth/login` | Email+password login, returns JWT |
| POST | `/auth/google` | Google OAuth login (scaffolded, needs `google-auth` wired in) |
| GET | `/auth/me` | Current authenticated user |

### Movies
| Method | Path | Description |
|---|---|---|
| GET | `/movies` | List/browse catalog (filter by genre, content_type) |
| GET | `/movies/{id}` | Single title |
| GET | `/movies/{id}/similar` | "Because you watched X" content-similarity rail |
| POST | `/movies/rate` | Rate (or update rating for) a title |
| POST | `/movies/watch-history` | Log a watch event (time, device, completion) |
| GET | `/movies/me/continue-watching` | In-progress titles |
| POST / DELETE | `/movies/watchlist` | Add/remove from "My List" |

### Recommendations
| Method | Path | Description |
|---|---|---|
| GET | `/recommendations/for-me` | Personalized hybrid recommendations |
| POST | `/recommendations/mood` | Mood-text → genre-matched recommendations |
| GET | `/recommendations/trending` | Real-time trending (watch activity + ratings) |
| GET | `/recommendations/taste-dna` | Genre breakdown + "viewing personality" |

### Search
| Method | Path | Description |
|---|---|---|
| GET | `/search?q=...` | Unified fuzzy + semantic search, with genre/actor/director filters |
| GET | `/search/suggestions?q=...` | Autocomplete |

### AI Assistant
| Method | Path | Description |
|---|---|---|
| POST | `/assistant/chat` | Retrieval-grounded chatbot: recommends, explains, adds to watchlist |

### Admin (requires `role=admin`)
| Method | Path | Description |
|---|---|---|
| GET | `/admin/analytics/overview` | Platform KPIs |
| GET | `/admin/analytics/engagement-by-day` | Daily watch activity |
| GET | `/admin/analytics/recommendation-accuracy` | Live Precision/Recall/NDCG/RMSE/MAE |
| POST | `/admin/model/refresh` | Refit the recommendation model against current DB data |
| POST / DELETE | `/admin/movies` | CMS: add/remove catalog titles |

### Real-time
`ws://localhost:8000/ws/live` — broadcasts trending updates to connected clients.

---

## Project layout

```
netflix-rec-system/
├── docker-compose.yml
├── .env.example
├── frontend/                          # "Aperture" -- Next.js 16 + Tailwind v4
│   ├── Dockerfile
│   ├── .env.local.example
│   ├── app/
│   │   ├── layout.tsx                 # fonts (Bebas Neue + Inter), film-grain layer
│   │   ├── page.tsx                   # home: hero, mood picker, recommendation rails
│   │   ├── login/, register/          # auth pages
│   │   ├── search/                    # unified search + autocomplete
│   │   ├── watchlist/                 # "My List"
│   │   ├── profile/                   # Taste DNA (signature constellation viz)
│   │   └── movie/[id]/                # detail page: rating, similar titles
│   ├── components/
│   │   ├── Header.tsx, HeroBanner.tsx (canvas particle field)
│   │   ├── MovieCard.tsx              # 3D tilt hover, watchlist toggle, reason tooltip
│   │   ├── MovieRail.tsx              # horizontal scroll rail, skeleton loading
│   │   └── MoodPicker.tsx             # AI mood-based search widget
│   └── lib/
│       ├── api.ts                     # typed fetch client for every backend endpoint
│       ├── auth-context.tsx           # React context: login/register/logout/JWT
│       └── types.ts                   # shared TS types mirroring backend schemas
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── pytest.ini
    ├── alembic.ini / alembic/        # DB migrations
    ├── data/                         # movies.csv / ratings.csv / tags.csv
    ├── scripts/
    │   ├── generate_sample_data.py   # synthetic MovieLens-shaped dataset
    │   ├── download_movielens.py     # fetches the real public dataset
    │   └── seed_database.py         # loads CSVs into Postgres + demo accounts
    ├── app/
    │   ├── main.py                   # FastAPI app, lifespan, router wiring
    │   ├── core/                     # config, db session, JWT/bcrypt, deps
    │   ├── models/db_models.py       # SQLAlchemy ORM models
    │   ├── schemas/                  # Pydantic request/response models
    │   ├── services/                 # RecommendationService, Redis cache
    │   ├── api/                      # auth, movies, recommendations, search,
    │   │                             # assistant, admin, websocket routers
    │   └── ml/
    │       ├── content_based.py      # TF-IDF + cosine similarity
    │       ├── collaborative.py      # Truncated SVD matrix factorization
    │       ├── hybrid.py             # blending + explainability + cold-start
    │       ├── neural_cf.py          # optional PyTorch NCF (lazy import)
    │       ├── mood_recommender.py   # mood-text → genre NLP mapping
    │       ├── search_service.py     # fuzzy + semantic search
    │       └── evaluation.py         # Precision@K/Recall@K/RMSE/MAE/NDCG/A-B
    └── tests/                        # 31 passing tests, isolated SQLite per test
```

---

## What's intentionally not included yet

Being upfront about scope: the original request covered an enormous surface
area (deep learning models in production, OAuth end-to-end, CI/CD pipelines,
cloud deployment, webcam emotion detection, friend-matching, A/B testing
infrastructure, Smart TV layouts, etc.). Building all of that to a genuinely
working standard in one pass isn't realistic, so this delivers a solid,
**fully working** full-stack core and is explicit about what's stubbed vs. real:

**Fully working and tested:**
- Hybrid recommendation engine (content-based + collaborative + blending)
- Mood-based NLP recommendations, semantic/fuzzy search, explainable AI
- JWT auth, bcrypt password hashing, RBAC, rate limiting
- Real-time trending, Taste DNA, AI chat assistant (retrieval-grounded)
- Redis caching with cache invalidation on new ratings
- Admin analytics + live ML evaluation (Precision@K, Recall@K, RMSE, MAE, NDCG)
- Docker Compose (Postgres + Redis + API + frontend), Alembic migrations, 31 passing backend tests
- Next.js frontend: auth flows, browsing rails, mood picker, unified search
  with autocomplete, watchlist, movie detail with star ratings, and a Taste
  DNA page with a custom radial "constellation" visualization. Builds clean
  with zero TypeScript errors.

**Scaffolded but not wired up (clearly marked in code with `NotImplementedError`/docstrings):**
- Google OAuth (`/auth/google` returns 501 until `google-auth` token
  verification is added — left honest rather than faking it; the frontend
  has no Google button yet either, for the same reason)
- Neural Collaborative Filtering (`app/ml/neural_cf.py` is a real PyTorch
  implementation, but lazy-imported since torch is a heavy dependency; not
  wired into the default hybrid blend)
- WebSocket trending broadcasts (the connection manager works; nothing calls
  `broadcast_trending_update()` on a schedule yet, and the frontend doesn't
  open the socket yet)

**Not started — natural next steps:**
- XGBoost/LightGBM ranking re-ranker, `surprise` library SVD++
- CI/CD pipeline (GitHub Actions), cloud deployment (AWS/Azure)
- Webcam emotion detection, AI friend-matching, recommendation timeline UI
- Admin analytics dashboard *UI* (the backend endpoints exist and work; no
  frontend page renders them yet)
- A/B testing *infrastructure* (the metrics/comparator function exists in
  `evaluation.py`'s `ab_test_compare`, but there's no traffic-splitting layer)

If you want to keep building, the highest-leverage next steps are probably:
(1) an admin dashboard UI for the analytics endpoints that already work,
(2) wiring Google OAuth for real, and (3) a scheduled job to call
`/admin/model/refresh` periodically instead of manually.
