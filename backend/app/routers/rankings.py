from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.rank import Rank, RankingSession
from app.models.user import User
from app.models.want_to_watch import WantToWatch
from app.schemas.movie import MovieOut
from app.schemas.rank import (
    AnswerRequest,
    RankingSessionOut,
    RankOut,
    StartRankingRequest,
)
from app.services import ranking
from app.services.tmdb import get_or_create_movie

router = APIRouter(prefix="/api/rankings", tags=["rankings"])


def _to_session_out(result: dict) -> RankingSessionOut:
    return RankingSessionOut(
        session_id=result["session_id"],
        done=result["done"],
        comparison_movie=MovieOut.model_validate(result["comparison_movie"])
        if result.get("comparison_movie")
        else None,
        result=RankOut.model_validate(result["result"]) if result.get("result") else None,
        total_comparisons_estimate=result.get("total_comparisons_estimate", 0),
        comparisons_made=result.get("comparisons_made", 0),
    )


@router.get("", response_model=list[RankOut])
def my_rankings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ranks = db.query(Rank).filter(Rank.user_id == current_user.id).order_by(Rank.score.desc()).all()
    return ranks


@router.get("/user/{user_id}", response_model=list[RankOut])
def user_rankings(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    ranks = db.query(Rank).filter(Rank.user_id == user_id).order_by(Rank.score.desc()).all()
    return ranks


@router.post("/sessions", response_model=RankingSessionOut)
async def start_ranking(
    payload: StartRankingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie = await get_or_create_movie(db, payload.tmdb_id)
    result = ranking.start_session(db, current_user, movie, payload.tier, payload.note)

    wtw = db.query(WantToWatch).filter(WantToWatch.user_id == current_user.id, WantToWatch.movie_id == movie.id).first()
    if wtw:
        db.delete(wtw)
        db.commit()

    return _to_session_out(result)


@router.post("/sessions/{session_id}/answer", response_model=RankingSessionOut)
def answer_ranking(
    session_id: int,
    payload: AnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.get(RankingSession, session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ranking session not found")
    if payload.winner not in ("new", "existing"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "winner must be 'new' or 'existing'")

    result = ranking.answer_session(db, current_user, session, payload.winner)
    return _to_session_out(result)


@router.delete("/{rank_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ranking(
    rank_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rank = db.get(Rank, rank_id)
    if rank is None or rank.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ranking not found")
    tier = rank.tier
    db.delete(rank)
    db.commit()
    remaining = ranking._tier_ranks_desc(db, current_user.id, tier)
    ranking._rebalance_tier(tier, remaining)
    db.commit()
