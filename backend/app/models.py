from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class Bucket(StrEnum):
    LOVED = "loved"
    FINE = "fine"
    BAD = "bad"


class DisplayMetric(StrEnum):
    LATEST = "latest"
    MEAN = "mean"
    MEDIAN = "median"


def _utcnow() -> datetime:
    return datetime.now()


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=_utcnow)

    movies: list["Movie"] = Relationship(back_populates="user", cascade_delete=True)  # noqa: UP037
    settings: Optional["UserSettings"] = Relationship(  # noqa: UP037, UP045
        back_populates="user",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )


class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"

    user_id: int = Field(foreign_key="users.id", primary_key=True, ondelete="CASCADE")
    display_metric: DisplayMetric = Field(default=DisplayMetric.LATEST)

    user: User = Relationship(back_populates="settings")


class Movie(SQLModel, table=True):
    __tablename__ = "movies"
    __table_args__ = (UniqueConstraint("user_id", "tmdb_id", name="uq_user_tmdb"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    tmdb_id: int = Field(index=True)
    title: str
    year: int | None = None
    poster_path: str | None = None
    genres: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    added_at: datetime = Field(default_factory=_utcnow)

    user: User = Relationship(back_populates="movies")
    rankings: list["Ranking"] = Relationship(  # noqa: UP037
        back_populates="movie",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "Ranking.created_at.desc()"},
    )
    watches: list["WatchEntry"] = Relationship(  # noqa: UP037
        back_populates="movie",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "WatchEntry.watched_on.desc()"},
    )


class Ranking(SQLModel, table=True):
    __tablename__ = "rankings"

    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movies.id", index=True, ondelete="CASCADE")
    bucket: Bucket
    score: float
    note: str | None = None
    created_at: datetime = Field(default_factory=_utcnow, index=True)

    movie: Movie = Relationship(back_populates="rankings")


class WatchEntry(SQLModel, table=True):
    __tablename__ = "watch_entries"

    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movies.id", index=True, ondelete="CASCADE")
    watched_on: date
    note: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    movie: Movie = Relationship(back_populates="watches")


class RankingSession(SQLModel, table=True):
    """Server-side binary-search state for an in-progress Beli ranking."""

    __tablename__ = "ranking_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    movie_id: int = Field(foreign_key="movies.id", ondelete="CASCADE")
    bucket: Bucket
    candidate_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    lo: int = 0
    hi: int = 0
    created_at: datetime = Field(default_factory=_utcnow)
