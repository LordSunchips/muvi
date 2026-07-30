from datetime import date, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import CurrentUser, SessionDep
from app.models import Bucket, Movie, UserSettings, WatchEntry
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
    created_at: datetime


class WatchOut(BaseModel):
    id: int
    watched_on: date
    note: str | None
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
    watches: list[WatchOut]


class AddWatchRequest(BaseModel):
    watched_on: date
    note: str | None = Field(default=None, max_length=2000)


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
    watches = sorted(list(movie.watches), key=lambda w: w.watched_on, reverse=True)
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
                created_at=r.created_at,
            )
            for r in rankings
        ],
        watches=[
            WatchOut(id=w.id, watched_on=w.watched_on, note=w.note, created_at=w.created_at)  # type: ignore[arg-type]
            for w in watches
        ],
    )


@router.post("/movies/{movie_id}/watches", response_model=WatchOut, status_code=status.HTTP_201_CREATED)
def add_watch(movie_id: int, payload: AddWatchRequest, user: CurrentUser, session: SessionDep) -> WatchOut:
    assert user.id is not None
    _authorized_movie(movie_id, user.id, session)
    watch = WatchEntry(movie_id=movie_id, watched_on=payload.watched_on, note=payload.note)
    session.add(watch)
    session.commit()
    session.refresh(watch)
    assert watch.id is not None
    return WatchOut(id=watch.id, watched_on=watch.watched_on, note=watch.note, created_at=watch.created_at)


@router.delete("/watches/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watch(watch_id: int, user: CurrentUser, session: SessionDep) -> None:
    watch = session.get(WatchEntry, watch_id)
    if watch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch not found")
    movie = session.get(Movie, watch.movie_id)
    if movie is None or movie.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch not found")
    session.delete(watch)
    session.commit()


# Also expose ranking history via the movie detail; standalone /rankings list would just duplicate it.
# Ranking deletion lives in routes/rank.py.
