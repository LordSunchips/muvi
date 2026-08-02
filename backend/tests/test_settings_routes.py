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


def test_default_settings_are_latest(client: TestClient) -> None:
    token = _token(client)
    body = client.get("/settings", headers={"Authorization": f"Bearer {token}"}).json()
    assert body["display_metric"] == "latest"


def test_update_settings_persists(client: TestClient) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch("/settings", json={"display_metric": "median"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["display_metric"] == "median"
    assert client.get("/settings", headers=headers).json()["display_metric"] == "median"


def test_display_metric_changes_library_score(client: TestClient) -> None:
    """After ranking a movie twice with very different scores, mean vs median vs latest should differ."""
    from datetime import datetime, timedelta

    from sqlmodel import Session

    from app.db import get_session
    from app.main import app
    from app.models import Bucket, Movie, Ranking

    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get("/movie/1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 1,
                    "title": "A",
                    "release_date": "2000-01-01",
                    "poster_path": None,
                    "runtime": 100,
                    "genres": [],
                },
            )
        )
        movie = client.post("/library", json={"tmdb_id": 1}, headers=headers).json()

    # Insert two rankings directly so we can control values.
    session_override = app.dependency_overrides[get_session]
    gen = session_override()
    session: Session = next(gen)  # type: ignore[assignment]
    base = datetime.now()
    m = session.get(Movie, movie["id"])
    assert m is not None
    session.add(Ranking(movie_id=m.id, bucket=Bucket.LOVED, score=9.0, created_at=base))  # type: ignore[arg-type]
    session.add(Ranking(movie_id=m.id, bucket=Bucket.FINE, score=5.0, created_at=base + timedelta(seconds=1)))  # type: ignore[arg-type]
    session.commit()

    # LATEST → 5.0
    latest_score = client.get("/library", headers=headers).json()[0]["score"]
    assert latest_score == 5.0

    # MEAN → 7.0
    client.patch("/settings", json={"display_metric": "mean"}, headers=headers)
    assert client.get("/library", headers=headers).json()[0]["score"] == 7.0

    # MEDIAN of two → 7.0 (same as mean here) — still worth asserting the endpoint respects it.
    client.patch("/settings", json={"display_metric": "median"}, headers=headers)
    assert client.get("/library", headers=headers).json()[0]["score"] == 7.0
