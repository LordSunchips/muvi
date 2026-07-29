from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import get_settings

TMDB_BASE_URL = "https://api.themoviedb.org/3"


def _year_from_release_date(release_date: str | None) -> int | None:
    if not release_date:
        return None
    try:
        return int(release_date[:4])
    except ValueError:
        return None


async def _request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    if not settings.tmdb_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB_API_KEY is not configured on the server",
        )
    query = {"api_key": settings.tmdb_api_key, **(params or {})}
    async with httpx.AsyncClient(base_url=TMDB_BASE_URL, timeout=10.0) as client:
        try:
            response = await client.get(path, params=query)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"TMDB request failed: {exc}") from exc
    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TMDB resource not found")
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"TMDB error: {response.text}")
    return response.json()


async def search_movies(query: str, page: int = 1) -> list[dict[str, Any]]:
    payload = await _request("/search/movie", {"query": query, "page": page, "include_adult": "false"})
    results = payload.get("results", [])
    return [
        {
            "tmdb_id": item["id"],
            "title": item.get("title") or item.get("original_title") or "",
            "year": _year_from_release_date(item.get("release_date")),
            "poster_path": item.get("poster_path"),
            "overview": item.get("overview"),
            "genre_ids": item.get("genre_ids", []),
        }
        for item in results
    ]


async def get_movie(tmdb_id: int) -> dict[str, Any]:
    payload = await _request(f"/movie/{tmdb_id}")
    return {
        "tmdb_id": payload["id"],
        "title": payload.get("title") or payload.get("original_title") or "",
        "year": _year_from_release_date(payload.get("release_date")),
        "poster_path": payload.get("poster_path"),
        "overview": payload.get("overview"),
        "runtime": payload.get("runtime"),
        "genres": [{"id": g["id"], "name": g["name"]} for g in payload.get("genres", [])],
    }


async def list_genres() -> list[dict[str, Any]]:
    payload = await _request("/genre/movie/list")
    return [{"id": g["id"], "name": g["name"]} for g in payload.get("genres", [])]
