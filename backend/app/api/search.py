from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ml.search_service import SearchService
from app.models.db_models import Movie, SearchHistory, User
from app.schemas.movie import MovieResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=list[MovieResponse])
def search_movies(
    q: str,
    genre: str | None = None,
    actor: str | None = None,
    director: str | None = None,
    content_type: str | None = None,
    top_k: int = 20,
    db: Session = Depends(get_db),
):
    """
    Unified search: blends fuzzy title matching + semantic (TF-IDF)
    similarity, then applies structured filters (genre/actor/director/type).
    Voice search: the frontend transcribes speech via the Web Speech API
    and sends the resulting text here as `q` -- no separate backend path.
    """
    service = RecommendationService.get_instance()
    if not service.is_ready() or service.movies_df is None:
        raise HTTPException(status_code=503, detail="Catalog is still loading. Try again shortly.")

    search_service = SearchService(service.movies_df)
    movie_ids = search_service.search(
        query=q, genre=genre, actor=actor, director=director, content_type=content_type, top_k=top_k
    )
    if not movie_ids:
        return []

    movies = db.query(Movie).filter(Movie.id.in_(movie_ids)).all()
    order = {mid: i for i, mid in enumerate(movie_ids)}
    return sorted(movies, key=lambda m: order.get(m.id, 999))


@router.get("/suggestions", response_model=list[str])
def search_suggestions(q: str, limit: int = 6):
    """AI search-suggestions / autocomplete-as-you-type."""
    service = RecommendationService.get_instance()
    if not service.is_ready() or service.movies_df is None:
        return []
    search_service = SearchService(service.movies_df)
    return search_service.suggestions(q, limit=limit)


@router.post("/log", status_code=204)
def log_search(
    q: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Records a search query against the user's history, feeding personalization + analytics."""
    db.add(SearchHistory(user_id=current_user.id, query=q))
    db.commit()
    return None
