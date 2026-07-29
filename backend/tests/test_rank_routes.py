"""HTTP-level tests for the rank routes.

These insert Movie rows directly since /library doesn't exist yet (task 5).
"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Movie, Ranking


def _auth_token(client: TestClient, email: str = "u@example.com") -> str:
    body = client.post("/auth/signup", json={"email": email, "password": "supersecret"}).json()
    return body["access_token"]


def _add_movie(session: Session, user_id: int, tmdb_id: int, title: str) -> Movie:
    movie = Movie(user_id=user_id, tmdb_id=tmdb_id, title=title, year=2000)
    session.add(movie)
    session.commit()
    session.refresh(movie)
    return movie


def test_rank_start_first_movie_finalizes(client: TestClient, session: Session) -> None:
    token = _auth_token(client)
    from app.security import decode_access_token

    user_id = decode_access_token(token)
    assert user_id is not None
    movie = _add_movie(session, user_id, tmdb_id=1, title="A")

    response = client.post(
        "/rank/start",
        json={"movie_id": movie.id, "bucket": "loved", "note": "great"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["done"] is True
    assert body["ranking"]["bucket"] == "loved"
    assert body["ranking"]["note"] == "great"
    assert 6.7 <= body["ranking"]["score"] <= 10.0


def test_rank_start_returns_session_when_bucket_has_members(client: TestClient, session: Session) -> None:
    token = _auth_token(client)
    from app.security import decode_access_token

    user_id = decode_access_token(token)
    assert user_id is not None
    a = _add_movie(session, user_id, tmdb_id=1, title="A")
    b = _add_movie(session, user_id, tmdb_id=2, title="B")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/rank/start", json={"movie_id": a.id, "bucket": "loved"}, headers=headers)
    response = client.post("/rank/start", json={"movie_id": b.id, "bucket": "loved"}, headers=headers)
    body = response.json()
    assert body["done"] is False
    assert body["session_id"] is not None
    assert body["opponent"]["movie_id"] == a.id


def test_full_rank_flow_via_http(client: TestClient, session: Session) -> None:
    token = _auth_token(client)
    from app.security import decode_access_token

    user_id = decode_access_token(token)
    assert user_id is not None
    headers = {"Authorization": f"Bearer {token}"}
    a = _add_movie(session, user_id, tmdb_id=1, title="A")
    b = _add_movie(session, user_id, tmdb_id=2, title="B")
    c = _add_movie(session, user_id, tmdb_id=3, title="C")

    client.post("/rank/start", json={"movie_id": a.id, "bucket": "loved"}, headers=headers)
    client.post("/rank/start", json={"movie_id": b.id, "bucket": "loved"}, headers=headers)

    start = client.post("/rank/start", json={"movie_id": c.id, "bucket": "loved"}, headers=headers).json()
    session_id = start["session_id"]
    opponent_id = start["opponent"]["movie_id"]

    # Prefer C over everything → C ends up on top.
    while True:
        step = client.post(
            f"/rank/{session_id}/compare",
            json={"winner_movie_id": c.id},
            headers=headers,
        ).json()
        if step["done"]:
            assert step["ranking"]["score"] == 10.0
            return
        opponent_id = step["opponent"]["movie_id"]
        assert opponent_id != c.id


def test_rank_start_rejects_other_users_movie(client: TestClient, session: Session) -> None:
    token_a = _auth_token(client, "a@example.com")
    token_b = _auth_token(client, "b@example.com")
    from app.security import decode_access_token

    user_a_id = decode_access_token(token_a)
    assert user_a_id is not None
    movie = _add_movie(session, user_a_id, tmdb_id=1, title="A")

    response = client.post(
        "/rank/start",
        json={"movie_id": movie.id, "bucket": "loved"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_rank_start_requires_auth(client: TestClient) -> None:
    response = client.post("/rank/start", json={"movie_id": 1, "bucket": "loved"})
    assert response.status_code in (401, 403)


def test_delete_ranking_removes_row(client: TestClient, session: Session) -> None:
    token = _auth_token(client)
    from app.security import decode_access_token

    user_id = decode_access_token(token)
    assert user_id is not None
    headers = {"Authorization": f"Bearer {token}"}
    movie = _add_movie(session, user_id, tmdb_id=1, title="A")
    start = client.post("/rank/start", json={"movie_id": movie.id, "bucket": "loved"}, headers=headers).json()
    ranking_id = start["ranking"]["id"]

    response = client.delete(f"/rankings/{ranking_id}", headers=headers)
    assert response.status_code == 204
    # Row is gone.
    assert session.get(Ranking, ranking_id) is None


def test_delete_ranking_rejects_other_users(client: TestClient, session: Session) -> None:
    token_a = _auth_token(client, "a@example.com")
    token_b = _auth_token(client, "b@example.com")
    from app.security import decode_access_token

    user_a_id = decode_access_token(token_a)
    assert user_a_id is not None
    movie = _add_movie(session, user_a_id, tmdb_id=1, title="A")
    start = client.post(
        "/rank/start",
        json={"movie_id": movie.id, "bucket": "loved"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()
    ranking_id = start["ranking"]["id"]

    response = client.delete(f"/rankings/{ranking_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404
    assert session.get(Ranking, ranking_id) is not None
