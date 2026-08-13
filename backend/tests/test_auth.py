from fastapi.testclient import TestClient
from sqlmodel import select


def test_signup_returns_token_and_user(client: TestClient) -> None:
    response = client.post("/auth/signup", json={"email": "a@example.com", "password": "supersecret"})
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "a@example.com"
    assert isinstance(body["user"]["id"], int)


def test_signup_rejects_duplicate_email(client: TestClient) -> None:
    client.post("/auth/signup", json={"email": "a@example.com", "password": "supersecret"})
    response = client.post("/auth/signup", json={"email": "a@example.com", "password": "differentpw"})
    assert response.status_code == 409


def test_signup_rejects_short_password(client: TestClient) -> None:
    response = client.post("/auth/signup", json={"email": "a@example.com", "password": "short"})
    assert response.status_code == 422


def test_login_success(client: TestClient) -> None:
    client.post("/auth/signup", json={"email": "a@example.com", "password": "supersecret"})
    response = client.post("/auth/login", json={"email": "a@example.com", "password": "supersecret"})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_wrong_password(client: TestClient) -> None:
    client.post("/auth/signup", json={"email": "a@example.com", "password": "supersecret"})
    response = client.post("/auth/login", json={"email": "a@example.com", "password": "wrongpassword"})
    assert response.status_code == 401


def test_login_unknown_email(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever"})
    assert response.status_code == 401


def test_token_authenticates_protected_route(client: TestClient) -> None:
    from fastapi import APIRouter

    from app.deps import CurrentUser
    from app.main import app

    router = APIRouter()

    @router.get("/_test_me")
    def me(user: CurrentUser) -> dict[str, int]:
        assert user.id is not None
        return {"id": user.id}

    app.include_router(router)
    try:
        token = client.post(
            "/auth/signup",
            json={"email": "a@example.com", "password": "supersecret"},
        ).json()["access_token"]
        response = client.get("/_test_me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["id"] > 0

        bad = client.get("/_test_me", headers={"Authorization": "Bearer not-a-real-token"})
        assert bad.status_code == 401
    finally:
        # Remove the test route so it doesn't leak into other tests.
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/_test_me"]


def _signup(client: TestClient, email: str = "a@example.com") -> str:
    return client.post("/auth/signup", json={"email": email, "password": "supersecret"}).json()["access_token"]


def test_delete_account_requires_auth(client: TestClient) -> None:
    assert client.delete("/auth/me").status_code == 401


def test_delete_account_removes_user_and_login(client: TestClient) -> None:
    token = _signup(client)
    response = client.delete("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204

    # The account is gone, not merely deactivated: the credentials no longer work...
    assert client.post("/auth/login", json={"email": "a@example.com", "password": "supersecret"}).status_code == 401
    # ...the old token no longer resolves to a user...
    assert client.get("/library", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    # ...and the address is free to sign up again.
    assert client.post("/auth/signup", json={"email": "a@example.com", "password": "supersecret"}).status_code == 201


def test_delete_account_cascades_user_data(client: TestClient, session) -> None:
    """Every table keyed to the user must be emptied, including `ranking_sessions`, which has no
    ORM relationship back to User and so isn't covered by SQLAlchemy's cascades."""
    from app.models import Movie, Ranking, RankingSession, UserSettings

    token = _signup(client)
    auth = {"Authorization": f"Bearer {token}"}
    user_id = client.post("/auth/login", json={"email": "a@example.com", "password": "supersecret"}).json()["user"][
        "id"
    ]

    movie = Movie(user_id=user_id, tmdb_id=603, title="The Matrix", year=1999, genres=[{"id": 28, "name": "Action"}])
    session.add(movie)
    session.commit()
    session.refresh(movie)
    session.add(Ranking(movie_id=movie.id, bucket="loved", score=9.0))
    session.add(RankingSession(user_id=user_id, movie_id=movie.id, bucket="loved", candidate_ids=[]))
    session.commit()

    assert client.delete("/auth/me", headers=auth).status_code == 204

    session.expire_all()
    assert session.exec(select(Movie).where(Movie.user_id == user_id)).all() == []
    assert session.exec(select(Ranking).where(Ranking.movie_id == movie.id)).all() == []
    assert session.exec(select(RankingSession).where(RankingSession.user_id == user_id)).all() == []
    assert session.get(UserSettings, user_id) is None
