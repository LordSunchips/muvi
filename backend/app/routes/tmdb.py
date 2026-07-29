from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app import tmdb
from app.deps import CurrentUser

router = APIRouter(prefix="/tmdb", tags=["tmdb"])


class Genre(BaseModel):
    id: int
    name: str


class MovieSearchResult(BaseModel):
    tmdb_id: int
    title: str
    year: int | None = None
    poster_path: str | None = None
    overview: str | None = None
    genre_ids: list[int] = []


class MovieDetail(BaseModel):
    tmdb_id: int
    title: str
    year: int | None = None
    poster_path: str | None = None
    overview: str | None = None
    runtime: int | None = None
    genres: list[Genre] = []


@router.get("/search", response_model=list[MovieSearchResult])
async def search(
    _: CurrentUser,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    page: Annotated[int, Query(ge=1, le=500)] = 1,
) -> list[dict]:
    return await tmdb.search_movies(q, page=page)


@router.get("/movie/{tmdb_id}", response_model=MovieDetail)
async def movie_detail(_: CurrentUser, tmdb_id: int) -> dict:
    return await tmdb.get_movie(tmdb_id)


@router.get("/genres", response_model=list[Genre])
async def genres(_: CurrentUser) -> list[dict]:
    return await tmdb.list_genres()
