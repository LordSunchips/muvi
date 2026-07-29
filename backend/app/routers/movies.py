from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.rank import Rank
from app.models.user import User
from app.schemas.movie import MovieOut, MovieSearchResult
from app.services.tmdb import get_or_create_movie, search_movies

router = APIRouter(prefix="/api/movies", tags=["movies"])


@router.get("/search", response_model=list[MovieSearchResult])
async def search(q: str = Query(min_length=1), _current_user: User = Depends(get_current_user)):
    return await search_movies(q)


@router.get("/{tmdb_id}", response_model=MovieOut)
async def get_movie(
    tmdb_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    movie = await get_or_create_movie(db, tmdb_id)
    return movie


@router.get("/{tmdb_id}/community", response_model=dict)
async def community_score(
    tmdb_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    movie = await get_or_create_movie(db, tmdb_id)
    ranks = db.query(Rank).filter(Rank.movie_id == movie.id).all()
    if not ranks:
        return {"average_score": None, "ranked_by_count": 0}
    avg = sum(r.score for r in ranks) / len(ranks)
    return {"average_score": round(avg, 2), "ranked_by_count": len(ranks)}
