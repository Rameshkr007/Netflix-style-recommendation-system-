from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.db_models import DeviceType, Movie, Rating, User, WatchHistory, WatchlistItem
from app.schemas.movie import (
    MovieResponse,
    RatingCreate,
    RatingResponse,
    WatchHistoryCreate,
    WatchlistCreate,
)
from app.services.cache import cache_invalidate_prefix
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("", response_model=list[MovieResponse])
def list_movies(
    genre: str | None = None,
    region: str | None = None,
    content_type: str | None = None,
    skip: int = 0,
    limit: int = Query(default=24, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Movie)
    if genre:
        query = query.filter(Movie.genres.ilike(f"%{genre}%"))
    if region:
        query = query.filter(Movie.synopsis.ilike(f"%{region.lower()} cinematic story%"))
    if content_type:
        query = query.filter(Movie.content_type == content_type)
    return query.offset(skip).limit(limit).all()


@router.get("/{movie_id}", response_model=MovieResponse)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")
    return movie


@router.get("/{movie_id}/similar", response_model=list[MovieResponse])
def get_similar_movies(movie_id: int, top_k: int = 10, db: Session = Depends(get_db)):
    """'Because you watched X' style rail for a single title."""
    service = RecommendationService.get_instance()
    if not service.is_ready():
        return []
    recs = service.similar_to(movie_id, top_k=top_k)
    movie_ids = [r.movie_id for r in recs]
    if not movie_ids:
        return []
    movies = db.query(Movie).filter(Movie.id.in_(movie_ids)).all()
    order = {mid: i for i, mid in enumerate(movie_ids)}
    return sorted(movies, key=lambda m: order.get(m.id, 999))


@router.post("/rate", response_model=RatingResponse)
def rate_movie(
    payload: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    existing = (
        db.query(Rating)
        .filter(Rating.user_id == current_user.id, Rating.movie_id == payload.movie_id)
        .first()
    )
    if existing:
        existing.rating = payload.rating
        db.commit()
        db.refresh(existing)
        rating_obj = existing
    else:
        rating_obj = Rating(user_id=current_user.id, movie_id=payload.movie_id, rating=payload.rating)
        db.add(rating_obj)
        db.commit()
        db.refresh(rating_obj)

    # this user's recommendations are now stale -- invalidate all cached
    # variants (different top_k values), not just one hardcoded size
    cache_invalidate_prefix(f"recs:user:{current_user.id}:")
    return rating_obj


@router.post("/watch-history", status_code=204)
def log_watch_history(
    payload: WatchHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    entry = WatchHistory(
        user_id=current_user.id,
        movie_id=payload.movie_id,
        watch_time_seconds=payload.watch_time_seconds,
        completed=payload.completed,
        device_type=DeviceType(payload.device_type),
    )
    db.add(entry)
    db.commit()
    return None


@router.get("/me/continue-watching", response_model=list[MovieResponse])
def continue_watching(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Titles the user started but did not mark as completed, most recent first."""
    entries = (
        db.query(WatchHistory)
        .filter(WatchHistory.user_id == current_user.id, WatchHistory.completed.is_(False))
        .order_by(WatchHistory.watched_at.desc())
        .limit(20)
        .all()
    )
    movie_ids = list({e.movie_id for e in entries})
    if not movie_ids:
        return []
    return db.query(Movie).filter(Movie.id.in_(movie_ids)).all()


@router.post("/watchlist", status_code=204)
def add_to_watchlist(
    payload: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    exists = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == current_user.id, WatchlistItem.movie_id == payload.movie_id)
        .first()
    )
    if not exists:
        db.add(WatchlistItem(user_id=current_user.id, movie_id=payload.movie_id))
        db.commit()
    return None


@router.delete("/watchlist/{movie_id}", status_code=204)
def remove_from_watchlist(
    movie_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db.query(WatchlistItem).filter(
        WatchlistItem.user_id == current_user.id, WatchlistItem.movie_id == movie_id
    ).delete()
    db.commit()
    return None


@router.get("/me/watchlist", response_model=list[MovieResponse])
def get_watchlist(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).all()
    movie_ids = [i.movie_id for i in items]
    if not movie_ids:
        return []
    return db.query(Movie).filter(Movie.id.in_(movie_ids)).all()
