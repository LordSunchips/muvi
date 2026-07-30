"""Beli-style ranking: pick a sentiment bucket, then binary-search against existing bucket members.

The user compares "which was better" one movie at a time; the algorithm narrows the insertion window
until it collapses to a single position, then writes a Ranking row snapshotted at that position's score.
Existing rankings are never mutated — score drift is accepted in exchange for stable history.
"""

from collections.abc import Sequence
from datetime import date

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Bucket, Movie, Ranking, RankingSession, User
from app.ranking.base import CompareResult, OpponentInfo, RankingAlgorithm, StartResult, score_for_position


def _latest_ranking_in_scope(session: Session, movie_id: int, genre_id: int | None) -> Ranking | None:
    """Latest ranking for ``movie_id`` in the given scope.

    - ``genre_id is None`` (global scope) → the latest ranking where ``Ranking.genre_id is None``.
    - ``genre_id`` set → the latest ranking with matching ``Ranking.genre_id`` (falls back to nothing;
      the caller decides how to treat "no ranking in this genre").
    """
    query = select(Ranking).where(Ranking.movie_id == movie_id)
    query = (
        query.where(Ranking.genre_id.is_(None))  # type: ignore[union-attr]
        if genre_id is None
        else query.where(Ranking.genre_id == genre_id)
    )
    return session.exec(query.order_by(Ranking.created_at.desc()).limit(1)).first()


def _bucket_candidates(
    session: Session,
    user: User,
    bucket: Bucket,
    exclude_movie_id: int,
    genre_id: int | None,
) -> list[Movie]:
    """User's movies whose latest in-scope ranking is in ``bucket``, best-first.

    When ``genre_id`` is set, only movies tagged with that genre and with an in-genre ranking count;
    the resulting opponents are the movies you've re-ranked within this genre.
    """
    movies = session.exec(select(Movie).where(Movie.user_id == user.id)).all()
    scored: list[tuple[float, Movie]] = []
    for movie in movies:
        if movie.id == exclude_movie_id:
            continue
        if genre_id is not None and not any(g.get("id") == genre_id for g in movie.genres):
            continue
        latest = _latest_ranking_in_scope(session, movie.id, genre_id)  # type: ignore[arg-type]
        if latest is None or latest.bucket != bucket:
            continue
        scored.append((latest.score, movie))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [movie for _, movie in scored]


def _opponent(movies: Sequence[Movie], index: int) -> OpponentInfo:
    m = movies[index]
    assert m.id is not None
    return OpponentInfo(movie_id=m.id, title=m.title, year=m.year, poster_path=m.poster_path)


def _finalize(
    session: Session,
    movie: Movie,
    bucket: Bucket,
    position: int,
    total: int,
    note: str | None,
    watched_on: date | None,
    genre_id: int | None,
) -> Ranking:
    score = score_for_position(position, total, bucket)
    ranking = Ranking(
        movie_id=movie.id,  # type: ignore[arg-type]
        bucket=bucket,
        score=score,
        note=note,
        watched_on=watched_on,
        genre_id=genre_id,
    )
    session.add(ranking)
    session.commit()
    session.refresh(ranking)
    return ranking


class BeliRanking(RankingAlgorithm):
    def start(
        self,
        session: Session,
        user: User,
        movie: Movie,
        bucket: Bucket,
        note: str | None = None,
        watched_on: date | None = None,
        genre_id: int | None = None,
    ) -> StartResult:
        candidates = _bucket_candidates(session, user, bucket, exclude_movie_id=movie.id or -1, genre_id=genre_id)
        if not candidates:
            ranking = _finalize(
                session, movie, bucket, position=0, total=1, note=note, watched_on=watched_on, genre_id=genre_id
            )
            return StartResult(done=True, ranking=ranking)

        assert movie.id is not None
        assert user.id is not None
        rank_session = RankingSession(
            user_id=user.id,
            movie_id=movie.id,
            bucket=bucket,
            candidate_ids=[m.id for m in candidates],  # type: ignore[misc]
            lo=0,
            hi=len(candidates),
            pending_note=note,
            pending_watched_on=watched_on,
            genre_id=genre_id,
        )
        session.add(rank_session)
        session.commit()
        session.refresh(rank_session)

        mid = (rank_session.lo + rank_session.hi) // 2
        return StartResult(done=False, session_id=rank_session.id, opponent=_opponent(candidates, mid))

    def compare(
        self,
        session: Session,
        rank_session: RankingSession,
        winner_movie_id: int,
    ) -> CompareResult:
        candidates_ids = list(rank_session.candidate_ids)
        mid = (rank_session.lo + rank_session.hi) // 2
        if not 0 <= mid < len(candidates_ids):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ranking session already complete")

        opponent_id = candidates_ids[mid]
        if winner_movie_id == rank_session.movie_id:
            # New movie won → it belongs at a better position (smaller index).
            rank_session.hi = mid
        elif winner_movie_id == opponent_id:
            # Opponent won → new movie belongs after this one.
            rank_session.lo = mid + 1
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"winner_movie_id {winner_movie_id} is neither the ranked movie nor the current opponent",
            )

        session.add(rank_session)
        session.commit()
        session.refresh(rank_session)

        if rank_session.lo >= rank_session.hi:
            movie = session.get(Movie, rank_session.movie_id)
            assert movie is not None
            ranking = _finalize(
                session,
                movie,
                rank_session.bucket,
                position=rank_session.lo,
                total=len(candidates_ids) + 1,
                note=rank_session.pending_note,
                watched_on=rank_session.pending_watched_on,
                genre_id=rank_session.genre_id,
            )
            session.delete(rank_session)
            session.commit()
            return CompareResult(done=True, ranking=ranking)

        next_mid = (rank_session.lo + rank_session.hi) // 2
        next_opponent_movie = session.get(Movie, candidates_ids[next_mid])
        assert next_opponent_movie is not None
        assert next_opponent_movie.id is not None
        opponent = OpponentInfo(
            movie_id=next_opponent_movie.id,
            title=next_opponent_movie.title,
            year=next_opponent_movie.year,
            poster_path=next_opponent_movie.poster_path,
        )
        return CompareResult(done=False, opponent=opponent)
