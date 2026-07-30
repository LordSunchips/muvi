from datetime import date, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.deps import CurrentUser, SessionDep
from app.models import Bucket, Movie, UserSettings
from app.scoring import computed_score

router = APIRouter(tags=["movies"])


class GenreOut(BaseModel):
    id: int
    name: str


class RankingOut(BaseModel):
    id: int
    movie_id: int
    bucket: Bucket
    score: float
    note: str | None
    watched_on: date | None
    created_at: datetime


class MovieDetail(BaseModel):
    id: int
    tmdb_id: int
    title: str
    year: int | None
    poster_path: str | None
    genres: list[GenreOut]
    added_at: datetime
    score: float | None
    bucket: Bucket | None
    rankings: list[RankingOut]


def _authorized_movie(movie_id: int, user_id: int, session) -> Movie:
    movie = session.get(Movie, movie_id)
    if movie is None or movie.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@router.get("/movies/{movie_id}", response_model=MovieDetail)
def movie_detail(movie_id: int, user: CurrentUser, session: SessionDep) -> MovieDetail:
    assert user.id is not None
    movie = _authorized_movie(movie_id, user.id, session)
    settings = session.get(UserSettings, user.id)
    metric = settings.display_metric if settings is not None else None

    rankings = sorted(list(movie.rankings), key=lambda r: r.created_at, reverse=True)
    latest = rankings[0] if rankings else None
    score = None
    if rankings and metric is not None:
        score = computed_score(rankings, metric)

    assert movie.id is not None
    return MovieDetail(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        title=movie.title,
        year=movie.year,
        poster_path=movie.poster_path,
        genres=[GenreOut(**g) for g in movie.genres],
        added_at=movie.added_at,
        score=score,
        bucket=latest.bucket if latest is not None else None,
        rankings=[
            RankingOut(
                id=r.id,  # type: ignore[arg-type]
                movie_id=r.movie_id,
                bucket=r.bucket,
                score=r.score,
                note=r.note,
                watched_on=r.watched_on,
                created_at=r.created_at,
            )
            for r in rankings
        ],
    )
