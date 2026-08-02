from fastapi.testclient import TestClient


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
