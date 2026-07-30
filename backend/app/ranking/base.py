from dataclasses import dataclass
from datetime import date
from typing import Protocol

from sqlmodel import Session

from app.models import Bucket, Movie, Ranking, RankingSession, User

# Inclusive score bands per bucket. Non-overlapping so a movie's score alone identifies its bucket.
BUCKET_BANDS: dict[Bucket, tuple[float, float]] = {
    Bucket.LOVED: (6.7, 10.0),
    Bucket.FINE: (3.4, 6.6),
    Bucket.BAD: (0.0, 3.3),
}


def score_for_position(position: int, total: int, bucket: Bucket) -> float:
    """Score assigned when inserting at ``position`` (0 = best) out of ``total`` total in the bucket.

    ``total`` is the count AFTER insertion. Positions 0 and total-1 map to the band's max and min.
    A single-item bucket lands at the band's midpoint.
    """
    if total < 1:
        raise ValueError("total must be >= 1")
    if not 0 <= position < total:
        raise ValueError(f"position {position} out of range for total {total}")
    low, high = BUCKET_BANDS[bucket]
    if total == 1:
        return round((low + high) / 2, 3)
    return round(high - position * (high - low) / (total - 1), 3)


@dataclass(slots=True)
class OpponentInfo:
    movie_id: int
    title: str
    year: int | None
    poster_path: str | None


@dataclass(slots=True)
class StartResult:
    """Return value of ``RankingAlgorithm.start``.

    If ``done`` is True, ``ranking`` is the finalized row and ``session_id``/``opponent`` are None.
    Otherwise ``session_id`` and ``opponent`` are set and the caller must call ``compare`` next.
    """

    done: bool
    ranking: Ranking | None = None
    session_id: int | None = None
    opponent: OpponentInfo | None = None


@dataclass(slots=True)
class CompareResult:
    """Return value of ``RankingAlgorithm.compare``.

    If ``done`` is True, the session is exhausted and ``ranking`` is the finalized row.
    Otherwise ``opponent`` is the next movie to compare against.
    """

    done: bool
    ranking: Ranking | None = None
    opponent: OpponentInfo | None = None


class RankingAlgorithm(Protocol):
    """Pluggable ranking algorithm.

    A future aspect-weighted algorithm can implement the same protocol; the routes stay unchanged.
    """

    def start(
        self,
        session: Session,
        user: User,
        movie: Movie,
        bucket: Bucket,
        note: str | None,
        watched_on: date | None,
    ) -> StartResult: ...

    def compare(
        self,
        session: Session,
        rank_session: RankingSession,
        winner_movie_id: int,
    ) -> CompareResult: ...
