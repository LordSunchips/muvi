"""`_utcnow` must return UTC even when the server's clock isn't.

These deliberately run under a non-UTC TZ. Asserting "is this UTC?" on a UTC host passes no
matter what the function does — that is precisely why the original bug survived: production runs
on a UTC container, so `datetime.now()` looked correct there and was five hours out locally.
"""

import os
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Movie, Ranking, User, _utcnow

pytestmark = pytest.mark.skipif(not hasattr(time, "tzset"), reason="TZ manipulation is POSIX-only")

TOLERANCE = timedelta(seconds=10)


@contextmanager
def server_timezone(name: str):
    """Run the block as though the host's clock were in ``name``.

    TZ is restored by hand rather than via monkeypatch: the env var and libc's cached zone have
    to be rolled back together, and a monkeypatch finalizer would run before the env is restored.
    """
    previous = os.environ.get("TZ")
    os.environ["TZ"] = name
    time.tzset()
    time.localtime()  # flush libc's cached zone; the first tzset in a process can otherwise
    try:  # not reach datetime.now(), making the first test silently vacuous
        yield
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()


def utc_wall_clock() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def assert_clock_shifted(zone: str, offset_hours: float) -> None:
    """Fail if the host clock didn't actually move into ``zone``.

    Without this the UTC-vs-UTC comparison passes whatever `_utcnow` does — the same blind spot
    that let the original bug reach production on a UTC container.
    """
    actual = (datetime.now() - utc_wall_clock()).total_seconds() / 3600
    assert actual == pytest.approx(offset_hours, abs=0.2), (
        f"TZ={zone} did not take effect: local clock is {actual:+.1f}h from UTC, expected {offset_hours:+.1f}h"
    )


# Etc/GMT signs are inverted: Etc/GMT-10 is UTC+10. Both directions, a half-hour zone, and UTC
# itself — the last one being the configuration that hid the bug.
@pytest.mark.parametrize(
    "zone,offset_hours",
    [("Etc/GMT-10", 10), ("Etc/GMT+9", -9), ("Etc/GMT-13", 13), ("Asia/Kolkata", 5.5), ("UTC", 0)],
)
def test_utcnow_is_utc_under_any_server_timezone(zone: str, offset_hours: float) -> None:
    with server_timezone(zone):
        assert_clock_shifted(zone, offset_hours)
        assert abs(_utcnow() - utc_wall_clock()) < TOLERANCE


def test_utcnow_does_not_follow_the_local_clock() -> None:
    """The direct regression: under UTC+10, local time is ten hours off and must not be used."""
    with server_timezone("Etc/GMT-10"):
        assert_clock_shifted("Etc/GMT-10", 10)
        local = datetime.now()
        stamped = _utcnow()
        assert abs(local - stamped) > timedelta(hours=9), (
            f"_utcnow() returned {stamped}, which tracks the local clock ({local}) rather than UTC"
        )


def test_utcnow_is_naive() -> None:
    """The columns are plain DATETIME. An aware value wouldn't survive the round trip, and would
    raise TypeError against the naive values already in the database."""
    assert _utcnow().tzinfo is None


@pytest.mark.parametrize("zone,offset_hours", [("Etc/GMT-10", 10), ("Etc/GMT+9", -9)])
def test_model_defaults_stamp_utc(zone: str, offset_hours: float) -> None:
    """Exercises the wiring, not just the helper — these defaults are what actually reach the DB
    and get rendered in the app's watch history."""
    with server_timezone(zone):
        assert_clock_shifted(zone, offset_hours)
        expected = utc_wall_clock()
        user = User(email="a@example.com", password_hash="hash")
        movie = Movie(user_id=1, tmdb_id=603, title="The Matrix")
        ranking = Ranking(movie_id=1, bucket="loved", score=9.0)

        for label, stamped in (
            ("User.created_at", user.created_at),
            ("Movie.added_at", movie.added_at),
            ("Ranking.created_at", ranking.created_at),
        ):
            assert abs(stamped - expected) < TOLERANCE, f"{label} is not UTC under {zone}"


def test_history_timestamps_round_trip_as_utc(client, session) -> None:
    """End to end: what the client reads back for a watch is UTC, which is how it decodes it.

    This is the shape of the original bug — the app parsed a naive timestamp as UTC and rendered
    a 23:54 CDT ranking as 6:54 PM.
    """
    with server_timezone("America/Chicago"):
        before = utc_wall_clock()
        token = client.post("/auth/signup", json={"email": "a@example.com", "password": "supersecret"}).json()[
            "access_token"
        ]
        auth = {"Authorization": f"Bearer {token}"}
        user_id = client.post("/auth/login", json={"email": "a@example.com", "password": "supersecret"}).json()["user"][
            "id"
        ]

        movie = Movie(user_id=user_id, tmdb_id=603, title="The Matrix", year=1999, genres=[])
        session.add(movie)
        session.commit()
        session.refresh(movie)

        started = client.post("/rank/start", json={"movie_id": movie.id, "bucket": "loved"}, headers=auth)
        assert started.status_code == 200
        created_at = datetime.fromisoformat(started.json()["ranking"]["created_at"])
        after = utc_wall_clock()

    assert before - TOLERANCE <= created_at <= after + TOLERANCE, (
        f"ranking timestamp {created_at} is outside the UTC window {before}..{after}"
    )
