from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Optional
from uuid import uuid4

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
    """Current UTC time, as a naive datetime.

    Was `datetime.now()`, which returns the server's *local* wall clock with no tzinfo — so the
    name was a lie everywhere but a UTC host. The iOS client reads a naive timestamp as UTC (see
    the decoder in APIClient.swift), so every stored time was displayed shifted by the server's
    offset: a ranking written at 23:54 CDT rendered in-app as 6:54 PM.

    Production hid it, because Render's container happens to run UTC. Local development did not.

    The tzinfo is stripped rather than kept: these map to plain DATETIME columns with no timezone,
    so SQLAlchemy would drop the offset on write anyway. Returning an aware value would only make
    the in-process type inconsistent with what comes back out of the database.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def _public_id() -> str:
    return uuid4().hex


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    # What access tokens carry as their subject — never `id`. SQLite reuses a rowid once the
    # highest row is deleted, so a user who deletes their account can hand their integer id to
    # the next person who signs up, and their week-long token would then authenticate as that
    # stranger. A random public id is never recycled, so a token outlives only its own account.
    public_id: str = Field(default_factory=_public_id, index=True, unique=True)
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


class Ranking(SQLModel, table=True):
    """A single ranking event for a movie.

    If ``watched_on`` is set, the user was logging that they watched the movie on that date
    (a "watch"). If it's null, this was a pure re-rank — the user adjusted the movie's
    position without logging a viewing.

    If ``genre_id`` is set, this ranking is scoped to that TMDB genre (e.g. drama's own list);
    if null, it's a global ranking against the user's whole library.
    """

    __tablename__ = "rankings"

    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movies.id", index=True, ondelete="CASCADE")
    bucket: Bucket
    score: float
    note: str | None = None
    watched_on: date | None = None
    genre_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=_utcnow, index=True)

    movie: Movie = Relationship(back_populates="rankings")


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
    pending_note: str | None = None
    pending_watched_on: date | None = None
    genre_id: int | None = None
    created_at: datetime = Field(default_factory=_utcnow)
