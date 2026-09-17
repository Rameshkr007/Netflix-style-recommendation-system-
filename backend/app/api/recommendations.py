from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ml.mood_recommender import MoodRecommender
from app.models.db_models import Movie, Rating, User, WatchHistory
from app.schemas.movie import MoodSearchRequest, MovieResponse, RecommendationItem
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _to_recommendation_items(recs, db: Session) -> list[RecommendationItem]:
    movie_ids = [r.movie_id for r in recs]
    if not movie_ids:
        return []
    movies = {m.id: m for m in db.query(Movie).filter(Movie.id.in_(movie_ids)).all()}
    items = []
    for r in recs:
        movie = movies.get(r.movie_id)
        if not movie:
            continue
        items.append(RecommendationItem(
            movie=MovieResponse.model_validate(movie),
            score=r.score,
            reason=r.reason,
            source=r.source,
        ))
    return items


@router.get("/for-me", response_model=list[RecommendationItem])
def get_my_recommendations(
    top_k: int = 12,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Main hybrid recommendation rail: collaborative + content-based, blended."""
    service = RecommendationService.get_instance()
    if not service.is_ready():
        raise HTTPException(status_code=503, detail="Recommendation model is still warming up. Try again shortly.")

    live_liked = [
        r.movie_id for r in
        db.query(Rating)
        .filter(Rating.user_id == current_user.id, Rating.rating >= 4.0)
        .order_by(Rating.rating.desc())
        .all()
    ]

    recs = service.recommend_for_user(current_user.id, top_k=top_k, live_liked_movie_ids=live_liked)
    return _to_recommendation_items(recs, db)


@router.post("/mood", response_model=list[MovieResponse])
def get_mood_based_recommendations(payload: MoodSearchRequest, db: Session = Depends(get_db)):
    """AI Mood-Based Recommendations: free-text mood -> matched genres -> ranked titles."""
    service = RecommendationService.get_instance()
    if not service.is_ready() or service.movies_df is None:
        raise HTTPException(status_code=503, detail="Catalog is still loading. Try again shortly.")

    mood_model = MoodRecommender(service.movies_df)
    result = mood_model.recommend(payload.mood_text, top_k=12)

    movies = db.query(Movie).filter(Movie.id.in_(result["movie_ids"])).all()
    order = {mid: i for i, mid in enumerate(result["movie_ids"])}
    return sorted(movies, key=lambda m: order.get(m.id, 999))


@router.get("/trending", response_model=list[MovieResponse])
def get_trending(limit: int = 20, db: Session = Depends(get_db)):
    """
    Real-Time Trending Engine: ranks titles by a blend of recent watch
    activity (last N watch_history rows) and average rating, so trending
    reflects what's actually being watched right now, not just all-time
    popularity.
    """
    watch_counts = (
        db.query(WatchHistory.movie_id, func.count(WatchHistory.id).label("watch_count"))
        .group_by(WatchHistory.movie_id)
        .subquery()
    )
    avg_ratings = (
        db.query(Rating.movie_id, func.avg(Rating.rating).label("avg_rating"))
        .group_by(Rating.movie_id)
        .subquery()
    )

    rows = (
        db.query(Movie, watch_counts.c.watch_count, avg_ratings.c.avg_rating)
        .outerjoin(watch_counts, Movie.id == watch_counts.c.movie_id)
        .outerjoin(avg_ratings, Movie.id == avg_ratings.c.movie_id)
        .all()
    )

    def trending_score(watch_count, avg_rating) -> float:
        wc = watch_count or 0
        ar = avg_rating or 3.0
        return wc * 1.0 + ar * 2.0  # watch activity weighted higher than static rating

    ranked = sorted(rows, key=lambda row: -trending_score(row[1], row[2]))
    return [row[0] for row in ranked[:limit]]


@router.get("/taste-dna")
def get_taste_dna(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    AI Taste DNA: aggregates a user's ratings into a genre-preference
    breakdown and a simple 'viewing personality' label, for the visual
    taste-profile feature.
    """
    ratings = (
        db.query(Rating, Movie)
        .join(Movie, Rating.movie_id == Movie.id)
        .filter(Rating.user_id == current_user.id)
        .all()
    )
    if not ratings:
        return {
            "genre_breakdown": {},
            "viewing_personality": "Unwritten -- rate a few titles to generate your Taste DNA.",
            "total_rated": 0,
        }

    genre_counter: Counter = Counter()
    genre_rating_sum: Counter = Counter()
    for rating, movie in ratings:
        for genre in movie.genres.split("|"):
            genre_counter[genre] += 1
            genre_rating_sum[genre] += rating.rating

    total = sum(genre_counter.values())
    breakdown = {
        genre: {
            "percentage": round(count / total * 100, 1),
            "avg_rating_given": round(genre_rating_sum[genre] / count, 2),
        }
        for genre, count in genre_counter.most_common()
    }

    top_genre = genre_counter.most_common(1)[0][0]
    personality_map = {
        "Action": "Thrill Seeker", "Drama": "Deep Feeler", "Comedy": "Mood Lifter",
        "Horror": "Adrenaline Chaser", "Sci-Fi": "Future Explorer", "Romance": "Hopeless Romantic",
        "Documentary": "Curious Mind", "Anime": "World Builder",
    }
    personality = personality_map.get(top_genre, "Eclectic Viewer")

    return {
        "genre_breakdown": breakdown,
        "viewing_personality": personality,
        "total_rated": len(ratings),
    }
