from pydantic import BaseModel


class MovieOut(BaseModel):
    id: int
    tmdb_id: int | None
    title: str
    year: int | None
    poster_path: str
    backdrop_path: str
    overview: str
    director: str
    runtime: int | None
    genres: str

    model_config = {"from_attributes": True}


class MovieSearchResult(BaseModel):
    tmdb_id: int
    title: str
    year: int | None
    poster_path: str
    overview: str


class AddMovieRequest(BaseModel):
    tmdb_id: int
