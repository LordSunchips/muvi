"""Beli-style dynamic rebalancing: existing scores update as the bucket grows or shrinks."""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import get_settings
from app.models import Movie, Ranking
from app.ranking.base import BUCKET_BANDS, Bucket
from app.tmdb import TMDB_BASE_URL


@pytest.fixture(autouse=True)
def _tmdb_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _token(client: TestClient, email: str = "u@example.com") -> str:
    return client.post("/auth/signup", json={"email": email, "password": "supersecret"}).json()["access_token"]


def _movie(tmdb_id: int, title: str) -> dict:
    return {
        "id": tmdb_id,
        "title": title,
        "release_date": "2000-01-01",
        "poster_path": None,
        "runtime": 100,
        "genres": [],
    }


def _add(client: TestClient, headers: dict, tmdb_id: int, title: str) -> dict:
    with respx.mock(base_url=TMDB_BASE_URL) as mock:
        mock.get(f"/movie/{tmdb_id}").mock(return_value=httpx.Response(200, json=_movie(tmdb_id, title)))
        return client.post("/library", json={"tmdb_id": tmdb_id}, headers=headers).json()


def _latest_score(session: Session, movie_id: int) -> float:
    row = session.exec(
        select(Ranking).where(Ranking.movie_id == movie_id).order_by(Ranking.created_at.desc()).limit(1)
    ).first()
    assert row is not None
    return row.score


def test_inserting_above_existing_movie_pushes_it_down(client: TestClient, session: Session) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    odyssey = _add(client, headers, 1, "Odyssey")
    new_movie = _add(client, headers, 2, "New")

    # Rank Odyssey alone in loved. It's the only one; midpoint (8.35).
    client.post("/rank/start", json={"movie_id": odyssey["id"], "bucket": "loved"}, headers=headers)
    assert _latest_score(session, odyssey["id"]) == pytest.approx(8.35)

    # Rank New into loved. Compare loop: New beats Odyssey (winner = New).
    start = client.post(
        "/rank/start",
        json={"movie_id": new_movie["id"], "bucket": "loved"},
        headers=headers,
    ).json()
    session_id = start["session_id"]
    client.post(
        f"/rank/{session_id}/compare",
        json={"winner_movie_id": new_movie["id"]},
        headers=headers,
    )

    # New should be at the top (10.0), Odyssey pushed to the bottom (6.7). Old midpoint is gone.
    session.expire_all()
    low, high = BUCKET_BANDS[Bucket.LOVED]
    assert _latest_score(session, new_movie["id"]) == pytest.approx(high)
    assert _latest_score(session, odyssey["id"]) == pytest.approx(low)


def test_deleting_ranking_rebalances_bucket(client: TestClient, session: Session) -> None:
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    a = _add(client, headers, 1, "A")
    b = _add(client, headers, 2, "B")
    c = _add(client, headers, 3, "C")

    # Set up: A best, B middle, C worst — by inserting in order and always beating the existing.
    client.post("/rank/start", json={"movie_id": a["id"], "bucket": "loved"}, headers=headers)
    # Insert B; user says A > B → B goes to bottom.
    s = client.post("/rank/start", json={"movie_id": b["id"], "bucket": "loved"}, headers=headers).json()
    client.post(f"/rank/{s['session_id']}/compare", json={"winner_movie_id": a["id"]}, headers=headers)
    # Insert C; user says A > C then B > C → C at bottom.
    s = client.post("/rank/start", json={"movie_id": c["id"], "bucket": "loved"}, headers=headers).json()
    step = client.post(
        f"/rank/{s['session_id']}/compare", json={"winner_movie_id": s["opponent"]["movie_id"]}, headers=headers
    ).json()
    if not step["done"]:
        client.post(
            f"/rank/{s['session_id']}/compare",
            json={"winner_movie_id": step["opponent"]["movie_id"]},
            headers=headers,
        )

    session.expire_all()
    low, high = BUCKET_BANDS[Bucket.LOVED]
    a_before = _latest_score(session, a["id"])
    b_before = _latest_score(session, b["id"])
    c_before = _latest_score(session, c["id"])
    # In a 3-movie bucket the scores are evenly spaced across the band.
    assert a_before == pytest.approx(high)
    assert c_before == pytest.approx(low)
    assert b_before == pytest.approx((high + low) / 2, abs=0.01)

    # Delete B's ranking. The bucket now has 2 movies (A best, C worst).
    b_ranking = session.exec(
        select(Ranking).where(Ranking.movie_id == b["id"]).order_by(Ranking.created_at.desc()).limit(1)
    ).first()
    assert b_ranking is not None
    resp = client.delete(f"/rankings/{b_ranking.id}", headers=headers)
    assert resp.status_code == 204

    session.expire_all()
    assert _latest_score(session, a["id"]) == pytest.approx(high)
    assert _latest_score(session, c["id"]) == pytest.approx(low)


def test_new_top_ranking_wins_score_tie_over_existing_top(client: TestClient, session: Session) -> None:
    """Regression: when the newly-inserted movie's score ties the old top's score, the newer
    ranking must take the better slot after rebalance. Reported on the Fine tier — a new movie
    the user just picked as "better" was ending up with a lower score than its opponent because
    the stable sort was preserving the older movie's position on ties."""
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    a = _add(client, headers, 1, "A")
    b = _add(client, headers, 2, "B")
    c = _add(client, headers, 3, "C")

    # Seed the FINE bucket with A best and B worst. After this A=6.6, B=3.4.
    client.post("/rank/start", json={"movie_id": a["id"], "bucket": "fine"}, headers=headers)
    s = client.post("/rank/start", json={"movie_id": b["id"], "bucket": "fine"}, headers=headers).json()
    client.post(f"/rank/{s['session_id']}/compare", json={"winner_movie_id": a["id"]}, headers=headers)

    session.expire_all()
    low, high = BUCKET_BANDS[Bucket.FINE]
    assert _latest_score(session, a["id"]) == pytest.approx(high)

    # Insert C and pick "C is better than A" — C should end up on top.
    s = client.post("/rank/start", json={"movie_id": c["id"], "bucket": "fine"}, headers=headers).json()
    step = client.post(
        f"/rank/{s['session_id']}/compare", json={"winner_movie_id": c["id"]}, headers=headers
    ).json()
    # If more compares are needed (against B), keep C winning too.
    while not step["done"]:
        step = client.post(
            f"/rank/{s['session_id']}/compare", json={"winner_movie_id": c["id"]}, headers=headers
        ).json()

    session.expire_all()
    assert _latest_score(session, c["id"]) == pytest.approx(high), "newly-ranked top movie should get the band max"
    assert _latest_score(session, a["id"]) < high, "the displaced old top should drop below the band max"
    assert _latest_score(session, b["id"]) == pytest.approx(low)


def test_rebalance_only_touches_latest_ranking(client: TestClient, session: Session) -> None:
    """Old ranking rows keep their historical scores so mean/median metrics see the full history."""
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    odyssey = _add(client, headers, 1, "Odyssey")
    other = _add(client, headers, 2, "Other")

    # First loved ranking for Odyssey (alone → midpoint 8.35).
    client.post("/rank/start", json={"movie_id": odyssey["id"], "bucket": "loved"}, headers=headers)
    first_odyssey_ranking = session.exec(
        select(Ranking).where(Ranking.movie_id == odyssey["id"]).order_by(Ranking.created_at.asc()).limit(1)
    ).first()
    assert first_odyssey_ranking is not None
    assert first_odyssey_ranking.score == pytest.approx(8.35)

    # Second loved ranking for Odyssey (still alone → still midpoint 8.35).
    client.post("/rank/start", json={"movie_id": odyssey["id"], "bucket": "loved"}, headers=headers)

    # Now insert Other above Odyssey. Odyssey's LATEST score should drop to 6.7; the earlier row
    # keeps its 8.35.
    s = client.post("/rank/start", json={"movie_id": other["id"], "bucket": "loved"}, headers=headers).json()
    client.post(f"/rank/{s['session_id']}/compare", json={"winner_movie_id": other["id"]}, headers=headers)

    session.expire_all()
    # First (historical) row unchanged.
    session.refresh(first_odyssey_ranking)
    assert first_odyssey_ranking.score == pytest.approx(8.35)
    # Latest row now at bottom of loved band.
    assert _latest_score(session, odyssey["id"]) == pytest.approx(6.7)
