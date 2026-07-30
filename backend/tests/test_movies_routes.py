"""Tests for the unified movie-detail endpoint after the watch+rank merge."""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.tmdb import TMDB_BASE_URL


@pytest.fixture(autouse=True)
def _tmdb_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _token(client: TestClient, email: str = "u@example.com") -> str:
    return client.post("/auth/signup", json={"email": email, "password": "supersecret"}).json()["access_token"]


def _tmdb_movie_response(tmdb_id: int, title: str) -> dict:
    return {
        "id": tmdb_id,
        "title": title,
        "release_date": "1999-10-15",
        "poster_path": "/p.jpg",
        "overview": "…",
        "runtime": 120,
        "genres": [{"id": 18, "name": "Drama"}],
    }


def _add_movie(client: TestClient, headers: dict, tmdb_id: int = 550, title: str = "Fight Club") -> dict:
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get(f"/movie/{tmdb_id}").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(tmdb_id, title)))
        return client.post("/library", json={"tmdb_id": tmdb_id}, headers=headers).json()


def test_movie_detail_empty_history(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add_movie(client, headers)
    body = client.get(f"/movies/{movie['id']}", headers=headers).json()
    assert body["title"] == "Fight Club"
    assert body["rankings"] == []
    assert body["score"] is None
    assert body["bucket"] is None
    assert "watches" not in body


def test_movie_detail_includes_rank_with_watched_on(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add_movie(client, headers)
    client.post(
        "/rank/start",
        json={"movie_id": movie["id"], "bucket": "loved", "note": "epic", "watched_on": "2024-05-01"},
        headers=headers,
    )
    body = client.get(f"/movies/{movie['id']}", headers=headers).json()
    assert len(body["rankings"]) == 1
    row = body["rankings"][0]
    assert row["bucket"] == "loved"
    assert row["note"] == "epic"
    assert row["watched_on"] == "2024-05-01"


def test_movie_detail_distinguishes_rerank_from_watch(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add_movie(client, headers)
    # A watch (watched_on set)
    client.post(
        "/rank/start",
        json={"movie_id": movie["id"], "bucket": "loved", "watched_on": "2024-05-01"},
        headers=headers,
    )
    # A pure re-rank (no watched_on)
    client.post(
        "/rank/start",
        json={"movie_id": movie["id"], "bucket": "loved"},
        headers=headers,
    )
    body = client.get(f"/movies/{movie['id']}", headers=headers).json()
    assert len(body["rankings"]) == 2
    watched_ons = [r["watched_on"] for r in body["rankings"]]
    assert set(watched_ons) == {"2024-05-01", None}


def test_movie_detail_rejects_other_users_movie(client: TestClient) -> None:
    token_a = _token(client, "a@example.com")
    token_b = _token(client, "b@example.com")
    movie = _add_movie(client, {"Authorization": f"Bearer {token_a}"})
    response = client.get(f"/movies/{movie['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404
