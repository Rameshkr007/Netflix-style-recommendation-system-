"""
AI Chat Assistant
--------------------
A retrieval-grounded chat endpoint that can recommend movies, explain why,
suggest genres, and build a watchlist from natural language. Built on
top of the same SearchService / HybridRecommender / MoodRecommender used
elsewhere, with simple intent detection -- this keeps the assistant's
answers grounded in the actual catalog rather than hallucinating titles
that don't exist, which is the real risk with movie-recommendation
chatbots backed by a generic LLM with no retrieval step.

To upgrade this to a free-form conversational assistant, pipe the
detected intent + retrieved candidates into an LLM call (Anthropic API)
with a system prompt instructing it to only mention titles present in
the provided candidate list -- never invent titles. The structure below
already separates "retrieval" from "response phrasing" so that swap is
contained to `_phrase_response`.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ml.mood_recommender import MoodRecommender
from app.ml.search_service import SearchService
from app.models.db_models import Movie, User, WatchlistItem
from app.schemas.movie import MovieResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])

GENRE_KEYWORDS = [
    "action", "comedy", "drama", "horror", "romance", "sci-fi", "thriller",
    "documentary", "anime", "fantasy", "crime", "mystery", "animation",
]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    reply: str
    intent: str
    movies: list[MovieResponse] = []


def _detect_intent(message: str) -> str:
    lower = message.lower()
    if any(w in lower for w in ["watchlist", "save this", "add to my list"]):
        return "watchlist_add"
    if any(w in lower for w in ["why", "explain", "reason"]):
        return "explain"
    if any(g in lower for g in GENRE_KEYWORDS):
        return "genre_recommend"
    if any(w in lower for w in ["feel", "mood", "feeling", "today i"]):
        return "mood_recommend"
    return "general_recommend"


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RecommendationService.get_instance()
    if not service.is_ready() or service.movies_df is None:
        raise HTTPException(status_code=503, detail="Catalog is still loading. Try again shortly.")

    intent = _detect_intent(payload.message)
    movies_df = service.movies_df

    if intent == "mood_recommend":
        mood_model = MoodRecommender(movies_df)
        result = mood_model.recommend(payload.message, top_k=6)
        movie_ids = result["movie_ids"]
        reply = (
            f"It sounds like you're feeling {result['detected_mood']}. "
            f"Here are some {', '.join(result['matched_genres'])} picks that fit that mood."
        )

    elif intent == "genre_recommend":
        matched_genre = next((g for g in GENRE_KEYWORDS if g in payload.message.lower()), None)
        search_service = SearchService(movies_df)
        movie_ids = search_service.search(query=matched_genre or "", genre=matched_genre, top_k=6)
        reply = f"Here are some great {matched_genre} picks from the catalog."

    elif intent == "watchlist_add":
        # naive: try to find a title mentioned in the message and add it
        search_service = SearchService(movies_df)
        movie_ids = search_service.fuzzy_title_match(payload.message, limit=1)
        if movie_ids:
            exists = (
                db.query(WatchlistItem)
                .filter(WatchlistItem.user_id == current_user.id, WatchlistItem.movie_id == movie_ids[0])
                .first()
            )
            if not exists:
                db.add(WatchlistItem(user_id=current_user.id, movie_id=movie_ids[0]))
                db.commit()
            reply = "Added that to your watchlist!"
        else:
            reply = "I couldn't find that title in the catalog -- could you tell me the exact name?"

    elif intent == "explain":
        recs = service.recommend_for_user(current_user.id, top_k=5)
        movie_ids = [r.movie_id for r in recs]
        if recs:
            reply = "Here's why I'm recommending these: " + " ".join(r.reason for r in recs[:3])
        else:
            reply = "Rate a few titles first and I'll be able to explain personalized picks for you!"

    else:  # general_recommend
        recs = service.recommend_for_user(current_user.id, top_k=6)
        movie_ids = [r.movie_id for r in recs]
        reply = "Based on your taste profile, here's what I'd recommend right now."

    movies = []
    if movie_ids:
        fetched = {m.id: m for m in db.query(Movie).filter(Movie.id.in_(movie_ids)).all()}
        order = {mid: i for i, mid in enumerate(movie_ids)}
        movies = sorted(fetched.values(), key=lambda m: order.get(m.id, 999))

    return ChatResponse(reply=reply, intent=intent, movies=movies)
