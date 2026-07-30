from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import select

from app import tmdb
from app.deps import CurrentUser, SessionDep
from app.models import Bucket, DisplayMetric, Movie, Ranking, UserSettings
from app.scoring import computed_score

router = APIRouter(prefix="/library", tags=["library"])


class GenreOut(BaseModel):
    id: int
    name: str


class AddMovieRequest(BaseModel):
    tmdb_id: int


class LibraryMovie(BaseModel):
    id: int
    tmdb_id: int
    title: str
    year: int | None
    poster_path: str | None
    genres: list[GenreOut]
    added_at: datetime
    score: float | None
    bucket: Bucket | None
    ranking_count: int


def _display_metric(session, user_id: int) -> DisplayMetric:
    settings = session.get(UserSettings, user_id)
    return settings.display_metric if settings is not None else DisplayMetric.LATEST


def _library_movie(
    movie: Movie,
    rankings: list[Ranking],
    metric: DisplayMetric,
    genre_id: int | None = None,
) -> LibraryMovie:
    """Build the LibraryMovie response for one movie.

    When ``genre_id`` is set, the displayed score prefers rankings scoped to that genre and only
    falls back to global ones if none exist. The ``bucket`` badge follows the same preference so the
    row reflects the genre-scoped view of the movie.
    """
    assert movie.id is not None
    # Pick the ranking whose bucket we display alongside the score.
    latest: Ranking | None = None
    if genre_id is not None:
        in_genre = [r for r in rankings if r.genre_id == genre_id]
        if in_genre:
            latest = max(in_genre, key=lambda r: r.created_at)
    if latest is None:
        globals_only = [r for r in rankings if r.genre_id is None]
        if globals_only:
            latest = max(globals_only, key=lambda r: r.created_at)
    return LibraryMovie(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        title=movie.title,
        year=movie.year,
        poster_path=movie.poster_path,
        genres=[GenreOut(**g) for g in movie.genres],
        added_at=movie.added_at,
        score=computed_score(rankings, metric, genre_id=genre_id),
        bucket=latest.bucket if latest is not None else None,
        ranking_count=len(rankings),
    )


@router.post("", response_model=LibraryMovie, status_code=status.HTTP_201_CREATED)
async def add_to_library(payload: AddMovieRequest, user: CurrentUser, session: SessionDep) -> LibraryMovie:
    existing = session.exec(select(Movie).where(Movie.user_id == user.id, Movie.tmdb_id == payload.tmdb_id)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Movie already in library")

    details = await tmdb.get_movie(payload.tmdb_id)
    assert user.id is not None
    movie = Movie(
        user_id=user.id,
        tmdb_id=details["tmdb_id"],
        title=details["title"],
        year=details.get("year"),
        poster_path=details.get("poster_path"),
        genres=details.get("genres", []),
    )
    session.add(movie)
    session.commit()
    session.refresh(movie)
    metric = _display_metric(session, user.id)
    return _library_movie(movie, rankings=[], metric=metric)


@router.get("", response_model=list[LibraryMovie])
def list_library(
    user: CurrentUser,
    session: SessionDep,
    genre_id: Annotated[int | None, Query(description="Filter to movies tagged with this TMDB genre id")] = None,
    bucket: Annotated[Bucket | None, Query(description="Filter by latest ranking bucket")] = None,
) -> list[LibraryMovie]:
    assert user.id is not None
    metric = _display_metric(session, user.id)
    movies = session.exec(select(Movie).where(Movie.user_id == user.id)).all()

    results: list[LibraryMovie] = []
    for movie in movies:
        if genre_id is not None and not any(g.get("id") == genre_id for g in movie.genres):
            continue
        rankings = list(movie.rankings)
        row = _library_movie(movie, rankings, metric, genre_id=genre_id)
        if bucket is not None and row.bucket != bucket:
            continue
        results.append(row)

    # Ranked movies first (by score desc), then unranked (by added_at desc).
    results.sort(
        key=lambda m: (m.score is None, -(m.score or 0.0), -m.added_at.timestamp()),
    )
    return results


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_library(movie_id: int, user: CurrentUser, session: SessionDep) -> None:
    movie = session.get(Movie, movie_id)
    if movie is None or movie.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not in library")
    session.delete(movie)
    session.commit()
