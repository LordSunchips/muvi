import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import get_settings
from app.models import Movie, Ranking
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


def test_add_to_library_creates_movie(client: TestClient, session: Session) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/movie/550").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(550, "Fight Club")))
        response = client.post("/library", json={"tmdb_id": 550}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["tmdb_id"] == 550
    assert body["title"] == "Fight Club"
    assert body["genres"] == [{"id": 18, "name": "Drama"}]
    assert body["score"] is None
    assert body["ranking_count"] == 0
    # Row exists.
    stored = session.exec(select(Movie).where(Movie.tmdb_id == 550)).first()
    assert stored is not None


def test_add_to_library_rejects_duplicate(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/movie/550").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(550, "Fight Club")))
        client.post("/library", json={"tmdb_id": 550}, headers=headers)
        response = client.post("/library", json={"tmdb_id": 550}, headers=headers)
    assert response.status_code == 409


def test_list_library_returns_ranked_movies_first(client: TestClient, session: Session) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/movie/1").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(1, "A")))
        mock.get("/movie/2").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(2, "B")))
        mock.get("/movie/3").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(3, "C")))
        a = client.post("/library", json={"tmdb_id": 1}, headers=headers).json()
        b = client.post("/library", json={"tmdb_id": 2}, headers=headers).json()
        client.post("/library", json={"tmdb_id": 3}, headers=headers).json()  # unranked

    client.post("/rank/start", json={"movie_id": a["id"], "bucket": "loved"}, headers=headers)
    client.post("/rank/start", json={"movie_id": b["id"], "bucket": "fine"}, headers=headers)

    body = client.get("/library", headers=headers).json()
    assert len(body) == 3
    # First two are ranked (loved > fine); unranked is last.
    assert body[0]["title"] == "A"
    assert body[0]["bucket"] == "loved"
    assert body[1]["title"] == "B"
    assert body[1]["bucket"] == "fine"
    assert body[2]["title"] == "C"
    assert body[2]["score"] is None


def test_list_library_filters_by_genre(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        drama = {**_tmdb_movie_response(1, "Drama"), "genres": [{"id": 18, "name": "Drama"}]}
        action = {**_tmdb_movie_response(2, "Action"), "genres": [{"id": 28, "name": "Action"}]}
        mock.get("/movie/1").mock(return_value=httpx.Response(200, json=drama))
        mock.get("/movie/2").mock(return_value=httpx.Response(200, json=action))
        client.post("/library", json={"tmdb_id": 1}, headers=headers)
        client.post("/library", json={"tmdb_id": 2}, headers=headers)

    body = client.get("/library", params={"genre_id": 28}, headers=headers).json()
    assert [m["title"] for m in body] == ["Action"]


def test_list_library_filters_by_bucket(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/movie/1").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(1, "L")))
        mock.get("/movie/2").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(2, "F")))
        a = client.post("/library", json={"tmdb_id": 1}, headers=headers).json()
        b = client.post("/library", json={"tmdb_id": 2}, headers=headers).json()
    client.post("/rank/start", json={"movie_id": a["id"], "bucket": "loved"}, headers=headers)
    client.post("/rank/start", json={"movie_id": b["id"], "bucket": "fine"}, headers=headers)
    body = client.get("/library", params={"bucket": "loved"}, headers=headers).json()
    assert [m["title"] for m in body] == ["L"]


def test_delete_from_library_cascades_rankings(client: TestClient, session: Session) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/movie/1").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(1, "A")))
        movie = client.post("/library", json={"tmdb_id": 1}, headers=headers).json()
    start = client.post("/rank/start", json={"movie_id": movie["id"], "bucket": "loved"}, headers=headers).json()
    ranking_id = start["ranking"]["id"]

    response = client.delete(f"/library/{movie['id']}", headers=headers)
    assert response.status_code == 204
    assert session.get(Movie, movie["id"]) is None
    assert session.get(Ranking, ranking_id) is None


def test_delete_from_library_rejects_other_user(client: TestClient) -> None:
    token_a = _token(client, "a@example.com")
    token_b = _token(client, "b@example.com")
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/movie/1").mock(return_value=httpx.Response(200, json=_tmdb_movie_response(1, "A")))
        movie = client.post("/library", json={"tmdb_id": 1}, headers={"Authorization": f"Bearer {token_a}"}).json()
    response = client.delete(f"/library/{movie['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404


def test_list_library_requires_auth(client: TestClient) -> None:
    assert client.get("/library").status_code in (401, 403)
