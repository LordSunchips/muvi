"""Tests for per-genre re-ranking end-to-end (algorithm + routes)."""

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


def _movie(tmdb_id: int, title: str, genres: list[dict]) -> dict:
    return {
        "id": tmdb_id,
        "title": title,
        "release_date": "2000-01-01",
        "poster_path": "/p.jpg",
        "overview": "…",
        "runtime": 100,
        "genres": genres,
    }


def _add(client: TestClient, headers: dict, tmdb_id: int, title: str, genres: list[dict]) -> dict:
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get(f"/movie/{tmdb_id}").mock(return_value=httpx.Response(200, json=_movie(tmdb_id, title, genres)))
        return client.post("/library", json={"tmdb_id": tmdb_id}, headers=headers).json()


DRAMA = {"id": 18, "name": "Drama"}
ACTION = {"id": 28, "name": "Action"}


def test_rank_with_genre_id_stores_it(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add(client, headers, 1, "A", [DRAMA])
    resp = client.post(
        "/rank/start",
        json={"movie_id": movie["id"], "bucket": "loved", "genre_id": 18},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["done"] is True
    assert body["ranking"]["genre_id"] == 18


def test_rank_rejects_genre_movie_isnt_tagged_with(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add(client, headers, 1, "A", [DRAMA])
    resp = client.post(
        "/rank/start",
        json={"movie_id": movie["id"], "bucket": "loved", "genre_id": 28},
        headers=headers,
    )
    assert resp.status_code == 400


def test_genre_scoped_candidates_only_include_in_genre_ranks(client: TestClient) -> None:
    """When ranking a movie within Drama, opponents come from other Drama-ranked movies only."""
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    a = _add(client, headers, 1, "A", [DRAMA])
    b = _add(client, headers, 2, "B", [DRAMA])
    c = _add(client, headers, 3, "C", [DRAMA])

    # A ranks LOVED globally, B ranks LOVED in Drama, C is fresh.
    client.post("/rank/start", json={"movie_id": a["id"], "bucket": "loved"}, headers=headers)
    client.post(
        "/rank/start",
        json={"movie_id": b["id"], "bucket": "loved", "genre_id": 18},
        headers=headers,
    )
    # Now rank C in Drama. Its opponent should be B (in-genre), not A (global-only).
    resp = client.post(
        "/rank/start",
        json={"movie_id": c["id"], "bucket": "loved", "genre_id": 18},
        headers=headers,
    ).json()
    assert resp["done"] is False
    assert resp["opponent"]["movie_id"] == b["id"]


def test_library_genre_filter_prefers_genre_scoped_score(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    a = _add(client, headers, 1, "A", [DRAMA])
    _add(client, headers, 2, "Action Only", [ACTION])

    # Global rank puts A in Bad, Drama-scoped rank puts A in Loved.
    client.post("/rank/start", json={"movie_id": a["id"], "bucket": "bad"}, headers=headers)
    client.post(
        "/rank/start",
        json={"movie_id": a["id"], "bucket": "loved", "genre_id": 18},
        headers=headers,
    )

    # Global library view uses the Bad ranking.
    global_body = client.get("/library", headers=headers).json()
    a_global = next(m for m in global_body if m["title"] == "A")
    assert a_global["bucket"] == "bad"
    assert a_global["score"] < 3.4

    # Drama-filtered view uses the Loved ranking.
    drama_body = client.get("/library", params={"genre_id": 18}, headers=headers).json()
    a_drama = next(m for m in drama_body if m["title"] == "A")
    assert a_drama["bucket"] == "loved"
    assert a_drama["score"] > 6.6
    # The action-only movie is filtered out.
    assert all(m["title"] != "Action Only" for m in drama_body)


def test_library_genre_filter_falls_back_to_global_when_no_genre_rank(client: TestClient) -> None:
    """A drama-tagged movie ranked globally shows its global rank in the drama filter."""
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    a = _add(client, headers, 1, "A", [DRAMA])
    client.post("/rank/start", json={"movie_id": a["id"], "bucket": "loved"}, headers=headers)

    drama_body = client.get("/library", params={"genre_id": 18}, headers=headers).json()
    assert len(drama_body) == 1
    assert drama_body[0]["bucket"] == "loved"


def test_movie_detail_returns_genre_id_on_rankings(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add(client, headers, 1, "A", [DRAMA])
    client.post("/rank/start", json={"movie_id": movie["id"], "bucket": "loved"}, headers=headers)
    client.post(
        "/rank/start",
        json={"movie_id": movie["id"], "bucket": "fine", "genre_id": 18},
        headers=headers,
    )
    body = client.get(f"/movies/{movie['id']}", headers=headers).json()
    assert len(body["rankings"]) == 2
    scoped = {r["genre_id"] for r in body["rankings"]}
    assert scoped == {None, 18}
