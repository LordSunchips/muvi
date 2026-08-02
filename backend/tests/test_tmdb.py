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


def _auth_header(client: TestClient) -> dict[str, str]:
    token = client.post(
        "/auth/signup",
        json={"email": "t@example.com", "password": "supersecret"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_search_returns_trimmed_results(client: TestClient) -> None:
    headers = _auth_header(client)
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/search/movie").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": 550,
                            "title": "Fight Club",
                            "original_title": "Fight Club",
                            "release_date": "1999-10-15",
                            "poster_path": "/poster.jpg",
                            "overview": "An insomniac...",
                            "genre_ids": [18, 53],
                        },
                        {
                            "id": 13,
                            "title": "Forrest Gump",
                            "release_date": "",
                            "poster_path": None,
                            "overview": None,
                            "genre_ids": [],
                        },
                    ]
                },
            )
        )
        response = client.get("/tmdb/search", params={"q": "fight"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body[0] == {
        "tmdb_id": 550,
        "title": "Fight Club",
        "year": 1999,
        "poster_path": "/poster.jpg",
        "overview": "An insomniac...",
        "genre_ids": [18, 53],
    }
    assert body[1]["year"] is None
    assert body[1]["poster_path"] is None


def test_search_requires_auth(client: TestClient) -> None:
    response = client.get("/tmdb/search", params={"q": "anything"})
    assert response.status_code == 401


def test_search_validates_query(client: TestClient) -> None:
    headers = _auth_header(client)
    response = client.get("/tmdb/search", params={"q": ""}, headers=headers)
    assert response.status_code == 422


def test_movie_detail(client: TestClient) -> None:
    headers = _auth_header(client)
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/movie/550").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 550,
                    "title": "Fight Club",
                    "release_date": "1999-10-15",
                    "poster_path": "/poster.jpg",
                    "overview": "Overview text",
                    "runtime": 139,
                    "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
                },
            )
        )
        response = client.get("/tmdb/movie/550", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["tmdb_id"] == 550
    assert body["year"] == 1999
    assert body["runtime"] == 139
    assert body["genres"] == [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}]


def test_movie_detail_404(client: TestClient) -> None:
    headers = _auth_header(client)
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/movie/99999999").mock(return_value=httpx.Response(404, json={"status_message": "Not found"}))
        response = client.get("/tmdb/movie/99999999", headers=headers)
    assert response.status_code == 404


def test_genres(client: TestClient) -> None:
    headers = _auth_header(client)
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/genre/movie/list").mock(
            return_value=httpx.Response(
                200,
                json={"genres": [{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}]},
            )
        )
        response = client.get("/tmdb/genres", headers=headers)
    assert response.status_code == 200
    assert response.json() == [{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}]


def test_missing_key_returns_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMDB_API_KEY", "")
    get_settings.cache_clear()
    headers = _auth_header(client)
    response = client.get("/tmdb/search", params={"q": "fight"}, headers=headers)
    assert response.status_code == 503
