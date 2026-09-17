from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MovieResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    genres: str
    year: int | None = None
    director: str | None = None
    cast: str | None = None
    content_type: str
    runtime_minutes: int | None = None
    poster_url: str | None = None
    synopsis: str | None = None


class MovieCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    genres: str = Field(min_length=1, max_length=255)
    year: int | None = None
    director: str | None = None
    cast: str | None = None
    content_type: str = "movie"
    runtime_minutes: int | None = None
    poster_url: str | None = None
    synopsis: str | None = None


class RatingCreate(BaseModel):
    movie_id: int
    rating: float = Field(ge=0.5, le=5.0)


class RatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    rating: float
    created_at: datetime


class WatchHistoryCreate(BaseModel):
    movie_id: int
    watch_time_seconds: int = Field(ge=0)
    completed: bool = False
    device_type: str = "desktop"


class WatchlistCreate(BaseModel):
    movie_id: int


class RecommendationItem(BaseModel):
    movie: MovieResponse
    score: float
    reason: str
    source: str


class MoodSearchRequest(BaseModel):
    mood_text: str = Field(min_length=1, max_length=500)


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)
