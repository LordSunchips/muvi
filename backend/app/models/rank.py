from datetime import datetime
from typing import TYPE_CHECKING
import enum

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import utcnow

if TYPE_CHECKING:
    from app.models.movie import Movie
    from app.models.user import User


class Tier(str, enum.Enum):
    LOVED = "loved"
    LIKED = "liked"
    DISLIKED = "disliked"


class Rank(Base):
    """A finalized, watched-and-scored movie for a user. Mirrors Beli's ranked list entry."""

    __tablename__ = "ranks"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_ranks_user_movie"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    tier: Mapped[Tier] = mapped_column(Enum(Tier))
    score: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="ranks")
    movie: Mapped["Movie"] = relationship()


class RankingSession(Base):
    """Ephemeral state for an in-progress pairwise ranking duel (binary insertion sort)."""

    __tablename__ = "ranking_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    tier: Mapped[Tier] = mapped_column(Enum(Tier))
    note: Mapped[str] = mapped_column(String(500), default="")
    # Comma-separated ordered rank IDs (best-to-worst) captured at session start.
    candidate_rank_ids: Mapped[str] = mapped_column(String(2000), default="")
    lo: Mapped[int] = mapped_column(Integer, default=0)
    hi: Mapped[int] = mapped_column(Integer, default=-1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
