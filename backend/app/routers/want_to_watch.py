from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.rank import Rank
from app.models.user import User
from app.models.want_to_watch import WantToWatch
from app.schemas.movie import AddMovieRequest, MovieOut
from app.services.tmdb import get_or_create_movie

router = APIRouter(prefix="/api/want-to-watch", tags=["want-to-watch"])


@router.get("", response_model=list[MovieOut])
def list_want_to_watch(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entries = (
        db.query(WantToWatch)
        .filter(WantToWatch.user_id == current_user.id)
        .order_by(WantToWatch.created_at.desc())
        .all()
    )
    return [e.movie for e in entries]


@router.post("", response_model=MovieOut, status_code=status.HTTP_201_CREATED)
async def add_want_to_watch(
    payload: AddMovieRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie = await get_or_create_movie(db, payload.tmdb_id)

    already_ranked = db.query(Rank).filter(Rank.user_id == current_user.id, Rank.movie_id == movie.id).first()
    if already_ranked:
        raise HTTPException(status.HTTP_409_CONFLICT, "You've already ranked this movie")

    existing = (
        db.query(WantToWatch).filter(WantToWatch.user_id == current_user.id, WantToWatch.movie_id == movie.id).first()
    )
    if existing:
        return movie

    db.add(WantToWatch(user_id=current_user.id, movie_id=movie.id))
    db.commit()
    return movie


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_want_to_watch(
    movie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = (
        db.query(WantToWatch).filter(WantToWatch.user_id == current_user.id, WantToWatch.movie_id == movie_id).first()
    )
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not in want-to-watch list")
    db.delete(entry)
    db.commit()
