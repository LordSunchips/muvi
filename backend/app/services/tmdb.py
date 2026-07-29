from typing import Any

from fastapi import HTTPException, status
import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.movie import Movie
from app.services.seed_movies import SEED_MOVIES

settings = get_settings()


def _using_fallback() -> bool:
    return not settings.tmdb_api_key


async def search_movies(query: str) -> list[dict[str, Any]]:
    query = query.strip()
    if not query:
        return []

    if _using_fallback():
        needle = query.lower()
        return [
            {
                "tmdb_id": m["tmdb_id"],
                "title": m["title"],
                "year": m["year"],
                "poster_path": m["poster_path"],
                "overview": m["overview"],
            }
            for m in SEED_MOVIES
            if needle in m["title"].lower()
        ]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.tmdb_base_url}/search/movie",
            params={
                "api_key": settings.tmdb_api_key,
                "query": query,
                "include_adult": "false",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for r in data.get("results", []):
        release_date = r.get("release_date") or ""
        year = int(release_date[:4]) if release_date[:4].isdigit() else None
        poster = r.get("poster_path") or ""
        results.append(
            {
                "tmdb_id": r["id"],
                "title": r.get("title") or r.get("original_title") or "Untitled",
                "year": year,
                "poster_path": f"{settings.tmdb_image_base_url}{poster}" if poster else "",
                "overview": r.get("overview") or "",
            }
        )
    return results


async def _fetch_details(tmdb_id: int) -> dict[str, Any]:
    if _using_fallback():
        for m in SEED_MOVIES:
            if m["tmdb_id"] == tmdb_id:
                return {**m, "backdrop_path": ""}
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movie not found")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.tmdb_base_url}/movie/{tmdb_id}",
            params={"api_key": settings.tmdb_api_key, "append_to_response": "credits"},
        )
        if resp.status_code == 404:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Movie not found")
        resp.raise_for_status()
        data = resp.json()

    director = ""
    for crew in data.get("credits", {}).get("crew", []):
        if crew.get("job") == "Director":
            director = crew.get("name", "")
            break

    release_date = data.get("release_date") or ""
    year = int(release_date[:4]) if release_date[:4].isdigit() else None
    poster = data.get("poster_path") or ""
    backdrop = data.get("backdrop_path") or ""

    return {
        "tmdb_id": tmdb_id,
        "title": data.get("title") or "Untitled",
        "year": year,
        "poster_path": f"{settings.tmdb_image_base_url}{poster}" if poster else "",
        "backdrop_path": f"{settings.tmdb_image_base_url}{backdrop}" if backdrop else "",
        "overview": data.get("overview") or "",
        "director": director,
        "runtime": data.get("runtime"),
        "genres": ", ".join(g["name"] for g in data.get("genres", [])),
    }


async def get_or_create_movie(db: Session, tmdb_id: int) -> Movie:
    movie = db.query(Movie).filter(Movie.tmdb_id == tmdb_id).one_or_none()
    if movie is not None:
        return movie

    details = await _fetch_details(tmdb_id)
    movie = Movie(
        tmdb_id=details["tmdb_id"],
        title=details["title"],
        year=details.get("year"),
        poster_path=details.get("poster_path", ""),
        backdrop_path=details.get("backdrop_path", ""),
        overview=details.get("overview", ""),
        director=details.get("director", ""),
        runtime=details.get("runtime"),
        genres=details.get("genres", ""),
    )
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie
