import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import get_settings
from app.models import WatchEntry
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


def test_movie_detail_includes_rankings_and_watches(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add_movie(client, headers)
    client.post("/rank/start", json={"movie_id": movie["id"], "bucket": "loved", "note": "sick"}, headers=headers)
    client.post(
        f"/movies/{movie['id']}/watches",
        json={"watched_on": "2024-05-01", "note": "with friends"},
        headers=headers,
    )

    body = client.get(f"/movies/{movie['id']}", headers=headers).json()
    assert body["title"] == "Fight Club"
    assert body["bucket"] == "loved"
    assert len(body["rankings"]) == 1
    assert body["rankings"][0]["note"] == "sick"
    assert len(body["watches"]) == 1
    assert body["watches"][0]["watched_on"] == "2024-05-01"
    assert body["watches"][0]["note"] == "with friends"


def test_movie_detail_rejects_other_users_movie(client: TestClient) -> None:
    token_a = _token(client, "a@example.com")
    token_b = _token(client, "b@example.com")
    movie = _add_movie(client, {"Authorization": f"Bearer {token_a}"})
    response = client.get(f"/movies/{movie['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404


def test_add_watch_returns_entry(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add_movie(client, headers)
    response = client.post(
        f"/movies/{movie['id']}/watches",
        json={"watched_on": "2024-05-01", "note": "hi"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["watched_on"] == "2024-05-01"
    assert body["note"] == "hi"
    assert body["id"] > 0


def test_add_watch_rejects_other_users_movie(client: TestClient) -> None:
    token_a = _token(client, "a@example.com")
    token_b = _token(client, "b@example.com")
    movie = _add_movie(client, {"Authorization": f"Bearer {token_a}"})
    response = client.post(
        f"/movies/{movie['id']}/watches",
        json={"watched_on": "2024-05-01"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_delete_watch_removes_row(client: TestClient, session: Session) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add_movie(client, headers)
    watch = client.post(
        f"/movies/{movie['id']}/watches",
        json={"watched_on": "2024-05-01"},
        headers=headers,
    ).json()

    response = client.delete(f"/watches/{watch['id']}", headers=headers)
    assert response.status_code == 204
    assert session.get(WatchEntry, watch["id"]) is None


def test_delete_watch_rejects_other_user(client: TestClient) -> None:
    token_a = _token(client, "a@example.com")
    token_b = _token(client, "b@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    movie = _add_movie(client, headers_a)
    watch = client.post(
        f"/movies/{movie['id']}/watches",
        json={"watched_on": "2024-05-01"},
        headers=headers_a,
    ).json()
    response = client.delete(f"/watches/{watch['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404
