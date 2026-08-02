from datetime import date, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import CurrentUser, SessionDep
from app.models import Bucket, Movie, Ranking, RankingSession
from app.ranking.base import OpponentInfo
from app.ranking.beli import BeliRanking

router = APIRouter(tags=["rank"])
_algorithm = BeliRanking()


class RankStartRequest(BaseModel):
    movie_id: int
    bucket: Bucket
    note: str | None = Field(default=None, max_length=2000)
    watched_on: date | None = None
    genre_id: int | None = None


class OpponentOut(BaseModel):
    movie_id: int
    title: str
    year: int | None
    poster_path: str | None


class RankingOut(BaseModel):
    id: int
    movie_id: int
    bucket: Bucket
    score: float
    note: str | None
    watched_on: date | None
    genre_id: int | None
    created_at: datetime


class RankStepOut(BaseModel):
    done: bool
    session_id: int | None = None
    opponent: OpponentOut | None = None
    ranking: RankingOut | None = None


class RankCompareRequest(BaseModel):
    winner_movie_id: int


class RankingUpdateRequest(BaseModel):
    """PATCH body for editing a logged watch. Both fields are full-replacement: send the value
    you want stored (or null to clear). Fields omitted from the body are left unchanged.
    """

    note: str | None = Field(default=None, max_length=2000)
    watched_on: date | None = None


def _opponent_out(op: OpponentInfo) -> OpponentOut:
    return OpponentOut(movie_id=op.movie_id, title=op.title, year=op.year, poster_path=op.poster_path)


def _ranking_out(r: Ranking) -> RankingOut:
    assert r.id is not None
    return RankingOut(
        id=r.id,
        movie_id=r.movie_id,
        bucket=r.bucket,
        score=r.score,
        note=r.note,
        watched_on=r.watched_on,
        genre_id=r.genre_id,
        created_at=r.created_at,
    )


@router.post("/rank/start", response_model=RankStepOut)
def rank_start(payload: RankStartRequest, user: CurrentUser, session: SessionDep) -> RankStepOut:
    movie = session.get(Movie, payload.movie_id)
    if movie is None or movie.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found in your library")
    if payload.genre_id is not None and not any(g.get("id") == payload.genre_id for g in movie.genres):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This movie isn't tagged with that genre",
        )
    result = _algorithm.start(
        session,
        user,
        movie,
        payload.bucket,
        note=payload.note,
        watched_on=payload.watched_on,
        genre_id=payload.genre_id,
    )
    if result.done:
        assert result.ranking is not None
        return RankStepOut(done=True, ranking=_ranking_out(result.ranking))
    assert result.opponent is not None
    return RankStepOut(done=False, session_id=result.session_id, opponent=_opponent_out(result.opponent))


@router.post("/rank/{session_id}/compare", response_model=RankStepOut)
def rank_compare(session_id: int, payload: RankCompareRequest, user: CurrentUser, session: SessionDep) -> RankStepOut:
    rank_session = session.get(RankingSession, session_id)
    if rank_session is None or rank_session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ranking session not found")
    result = _algorithm.compare(session, rank_session, payload.winner_movie_id)
    if result.done:
        assert result.ranking is not None
        return RankStepOut(done=True, ranking=_ranking_out(result.ranking))
    assert result.opponent is not None
    return RankStepOut(done=False, session_id=session_id, opponent=_opponent_out(result.opponent))


@router.patch("/rankings/{ranking_id}", response_model=RankingOut)
def update_ranking(
    ranking_id: int, payload: RankingUpdateRequest, user: CurrentUser, session: SessionDep
) -> RankingOut:
    """Edit a ranking's captured watch metadata (note and/or watched_on).

    Bucket, score, and genre scope are intentionally NOT editable here — changing those means
    re-running the ranking flow so the algorithm can re-place the movie against its peers.
    """
    ranking = session.get(Ranking, ranking_id)
    if ranking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ranking not found")
    movie = session.get(Movie, ranking.movie_id)
    if movie is None or movie.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ranking not found")
    updates = payload.model_dump(exclude_unset=True)
    if "note" in updates:
        ranking.note = updates["note"] or None
    if "watched_on" in updates:
        ranking.watched_on = updates["watched_on"]
    session.add(ranking)
    session.commit()
    session.refresh(ranking)
    return _ranking_out(ranking)


@router.delete("/rankings/{ranking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ranking(ranking_id: int, user: CurrentUser, session: SessionDep) -> None:
    ranking = session.get(Ranking, ranking_id)
    if ranking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ranking not found")
    movie = session.get(Movie, ranking.movie_id)
    if movie is None or movie.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ranking not found")
    _algorithm.remove(session, ranking)
