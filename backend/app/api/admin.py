from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.ml.evaluation import evaluate_hybrid_model, train_test_split_by_time
from app.models.db_models import Movie, Rating, SearchHistory, User, WatchHistory
from app.schemas.movie import MovieCreate, MovieResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/admin", tags=["Admin / Analytics"], dependencies=[Depends(require_admin)])


@router.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db)):
    """High-level platform KPIs for the admin dashboard landing view."""
    total_users = db.query(func.count(User.id)).scalar()
    total_movies = db.query(func.count(Movie.id)).scalar()
    total_ratings = db.query(func.count(Rating.id)).scalar()
    total_watch_events = db.query(func.count(WatchHistory.id)).scalar()
    total_watch_seconds = db.query(func.coalesce(func.sum(WatchHistory.watch_time_seconds), 0)).scalar()
    avg_rating = db.query(func.coalesce(func.avg(Rating.rating), 0)).scalar()

    return {
        "total_users": total_users,
        "total_titles": total_movies,
        "total_ratings": total_ratings,
        "total_watch_events": total_watch_events,
        "total_watch_hours": round((total_watch_seconds or 0) / 3600, 1),
        "average_rating": round(float(avg_rating or 0), 2),
    }


@router.get("/analytics/engagement-by-day")
def engagement_by_day(days: int = 14, db: Session = Depends(get_db)):
    """Daily watch-event counts for an engagement-over-time chart."""
    rows = (
        db.query(
            func.date(WatchHistory.watched_at).label("day"),
            func.count(WatchHistory.id).label("events"),
            func.coalesce(func.sum(WatchHistory.watch_time_seconds), 0).label("watch_seconds"),
        )
        .group_by(func.date(WatchHistory.watched_at))
        .order_by(func.date(WatchHistory.watched_at).desc())
        .limit(days)
        .all()
    )
    return [
        {"date": str(r.day), "watch_events": r.events, "watch_hours": round(r.watch_seconds / 3600, 2)}
        for r in reversed(rows)
    ]


@router.get("/analytics/top-search-queries")
def top_search_queries(limit: int = 15, db: Session = Depends(get_db)):
    rows = (
        db.query(SearchHistory.query, func.count(SearchHistory.id).label("count"))
        .group_by(SearchHistory.query)
        .order_by(func.count(SearchHistory.id).desc())
        .limit(limit)
        .all()
    )
    return [{"query": r.query, "count": r.count} for r in rows]


@router.get("/analytics/device-breakdown")
def device_breakdown(db: Session = Depends(get_db)):
    rows = (
        db.query(WatchHistory.device_type, func.count(WatchHistory.id).label("count"))
        .group_by(WatchHistory.device_type)
        .all()
    )
    return [{"device_type": r.device_type.value, "count": r.count} for r in rows]


@router.get("/analytics/recommendation-accuracy")
def recommendation_accuracy(k: int = 10, db: Session = Depends(get_db)):
    """
    Runs the offline evaluation suite (Precision@K, Recall@K, RMSE, MAE,
    NDCG@K) against current production data, for the 'Recommendation
    Accuracy' panel of the admin dashboard.
    """
    service = RecommendationService.get_instance()
    if not service.is_ready():
        return {"error": "Model not yet trained. Trigger /admin/model/refresh first."}

    ratings = db.query(Rating).all()
    if len(ratings) < 20:
        return {"error": "Not enough rating data yet for a meaningful offline evaluation."}

    import pandas as pd
    ratings_df = pd.DataFrame([
        {"userId": r.user_id, "movieId": r.movie_id, "rating": r.rating, "timestamp": r.created_at.timestamp()}
        for r in ratings
    ])
    _, test_df = train_test_split_by_time(ratings_df, test_fraction=0.2)
    result = evaluate_hybrid_model(service.model, test_df, k=k)
    return result.as_dict()


@router.post("/model/refresh", status_code=200)
def refresh_model(db: Session = Depends(get_db)):
    """Manually trigger a refit of the recommendation model against current DB contents."""
    service = RecommendationService.get_instance()
    service.refresh(db)
    return {"status": "refreshed", "is_ready": service.is_ready()}


@router.post("/movies", response_model=MovieResponse, status_code=201)
def create_movie(payload: MovieCreate, db: Session = Depends(get_db)):
    """CMS: add a new title to the catalog. Remember to call /admin/model/refresh afterward."""
    movie = Movie(
        title=payload.title,
        genres=payload.genres,
        year=payload.year,
        director=payload.director,
        cast=payload.cast,
        content_type=payload.content_type,
        runtime_minutes=payload.runtime_minutes,
        poster_url=payload.poster_url,
        synopsis=payload.synopsis,
    )
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie


@router.delete("/movies/{movie_id}", status_code=204)
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    db.query(Movie).filter(Movie.id == movie_id).delete()
    db.commit()
    return None
