"""
SQLAlchemy ORM models.

Schema overview:
  users           -- auth + profile + role (RBAC)
  movies          -- content catalog (movies/tv_shows/anime/documentaries)
  ratings         -- explicit user ratings (1 row per user-movie pair, used by CF)
  watch_history   -- implicit behavior signal: what was watched, how long, on what device
  search_history  -- query log, powers "AI search suggestions" and analytics
  watchlist_items -- "My List" -- user-saved-for-later titles
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, PyEnum):
    USER = "user"
    ADMIN = "admin"


class DeviceType(str, PyEnum):
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"
    SMART_TV = "smart_tv"


class ContentType(str, PyEnum):
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    ANIME = "anime"
    DOCUMENTARY = "documentary"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)  # nullable for OAuth-only users
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)

    # OAuth
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    favorite_genres: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma-separated
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    ratings: Mapped[list["Rating"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    watch_history: Mapped[list["WatchHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    search_history: Mapped[list["SearchHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    genres: Mapped[str] = mapped_column(String(255), nullable=False)  # "Action|Drama"
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    director: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cast: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[ContentType] = mapped_column(Enum(ContentType), default=ContentType.MOVIE)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    ratings: Mapped[list["Rating"]] = relationship(back_populates="movie", cascade="all, delete-orphan")


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_user_movie_rating"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)  # 0.5 - 5.0
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="ratings")
    movie: Mapped["Movie"] = relationship(back_populates="ratings")


class WatchHistory(Base):
    __tablename__ = "watch_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    watch_time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    device_type: Mapped[DeviceType] = mapped_column(Enum(DeviceType), default=DeviceType.DESKTOP)
    watched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="watch_history")
    movie: Mapped["Movie"] = relationship()


class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    searched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="search_history")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_user_movie_watchlist"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="watchlist_items")
    movie: Mapped["Movie"] = relationship()
