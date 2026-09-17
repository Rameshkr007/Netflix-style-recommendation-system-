"""
Application entrypoint.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Run via Docker:
    docker compose up

Interactive API docs available at /docs (Swagger) and /redoc.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, assistant, auth, movies, recommendations, search, websocket
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.deps import rate_limiter
from app.services.recommendation_service import RecommendationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("netflix_rec")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist yet. For real schema evolution use
    # Alembic migrations (see backend/alembic/) instead of relying on this
    # in production -- create_all() never alters existing tables.
    Base.metadata.create_all(bind=engine)

    # Warm up the recommendation model so the first request isn't slow.
    db = SessionLocal()
    try:
        service = RecommendationService.get_instance()
        service.refresh(db)
        logger.info("Recommendation model ready: %s", service.is_ready())
    except Exception as exc:
        logger.warning("Could not warm up recommendation model at startup: %s", exc)
    finally:
        db.close()

    yield  # application runs here

    # (no teardown needed -- SQLAlchemy connection pool closes with the process)


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Production-grade hybrid recommendation engine API: collaborative + "
        "content-based filtering, mood-based NLP recommendations, semantic "
        "search, an AI chat assistant, real-time trending, and an admin "
        "analytics dashboard backend."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All routers share the global rate limiter dependency.
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(rate_limiter)])
app.include_router(movies.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(rate_limiter)])
app.include_router(recommendations.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(rate_limiter)])
app.include_router(search.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(rate_limiter)])
app.include_router(assistant.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(rate_limiter)])
app.include_router(admin.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(rate_limiter)])
app.include_router(websocket.router)  # no REST rate limiting on the socket handshake


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/health", tags=["Health"])
def health_check():
    service = RecommendationService.get_instance()
    return {"status": "ok", "model_ready": service.is_ready()}
