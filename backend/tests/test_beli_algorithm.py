"""Pure-algorithm tests for BeliRanking.

These exercise the ranking module directly against an in-memory SQLite session, bypassing HTTP.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import Bucket, Movie, Ranking, User
from app.ranking.base import BUCKET_BANDS, score_for_position
from app.ranking.beli import BeliRanking
from app.security import hash_password


def _mk_user(session: Session, email: str = "u@example.com") -> User:
    user = User(email=email, password_hash=hash_password("supersecret"))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _mk_movie(session: Session, user: User, tmdb_id: int, title: str) -> Movie:
    movie = Movie(user_id=user.id, tmdb_id=tmdb_id, title=title, year=2000)  # type: ignore[arg-type]
    session.add(movie)
    session.commit()
    session.refresh(movie)
    return movie


# ---------------------------- score_for_position -----------------------------


def test_score_for_position_single_item_lands_at_midpoint() -> None:
    low, high = BUCKET_BANDS[Bucket.LOVED]
    assert score_for_position(0, 1, Bucket.LOVED) == round((low + high) / 2, 3)


def test_score_for_position_endpoints_match_band() -> None:
    low, high = BUCKET_BANDS[Bucket.FINE]
    assert score_for_position(0, 5, Bucket.FINE) == round(high, 3)
    assert score_for_position(4, 5, Bucket.FINE) == round(low, 3)


def test_score_for_position_is_monotonic_across_positions() -> None:
    scores = [score_for_position(i, 10, Bucket.LOVED) for i in range(10)]
    assert scores == sorted(scores, reverse=True)


def test_score_for_position_rejects_bad_input() -> None:
    import pytest

    with pytest.raises(ValueError):
        score_for_position(0, 0, Bucket.BAD)
    with pytest.raises(ValueError):
        score_for_position(3, 3, Bucket.BAD)
    with pytest.raises(ValueError):
        score_for_position(-1, 3, Bucket.BAD)


def test_bucket_bands_are_non_overlapping_and_ordered() -> None:
    loved_low, loved_high = BUCKET_BANDS[Bucket.LOVED]
    fine_low, fine_high = BUCKET_BANDS[Bucket.FINE]
    bad_low, bad_high = BUCKET_BANDS[Bucket.BAD]
    assert loved_high >= loved_low > fine_high >= fine_low > bad_high >= bad_low
    assert bad_low == 0.0
    assert loved_high == 10.0


# ------------------------------ BeliRanking.start -----------------------------


def test_first_ranking_in_empty_bucket_finalizes_immediately(session: Session) -> None:
    algo = BeliRanking()
    user = _mk_user(session)
    movie = _mk_movie(session, user, tmdb_id=1, title="Solo")

    result = algo.start(session, user, movie, Bucket.LOVED, note="first!")
    assert result.done is True
    assert result.session_id is None
    assert result.opponent is None
    assert result.ranking is not None
    low, high = BUCKET_BANDS[Bucket.LOVED]
    assert result.ranking.score == round((low + high) / 2, 3)
    assert result.ranking.note == "first!"


def test_second_ranking_starts_binary_search(session: Session) -> None:
    algo = BeliRanking()
    user = _mk_user(session)
    a = _mk_movie(session, user, tmdb_id=1, title="A")
    b = _mk_movie(session, user, tmdb_id=2, title="B")

    algo.start(session, user, a, Bucket.LOVED, note=None)
    result = algo.start(session, user, b, Bucket.LOVED, note="need to compare")

    assert result.done is False
    assert result.session_id is not None
    assert result.opponent is not None
    assert result.opponent.movie_id == a.id
    # pending_note is preserved on the session for finalize.
    from app.models import RankingSession

    rs = session.get(RankingSession, result.session_id)
    assert rs is not None
    assert rs.pending_note == "need to compare"


def test_start_ignores_other_buckets_and_other_users(session: Session) -> None:
    algo = BeliRanking()
    user = _mk_user(session, "a@example.com")
    other = _mk_user(session, "b@example.com")
    mine_loved = _mk_movie(session, user, tmdb_id=1, title="MineLoved")
    mine_fine = _mk_movie(session, user, tmdb_id=2, title="MineFine")
    theirs = _mk_movie(session, other, tmdb_id=3, title="Theirs")

    algo.start(session, user, mine_loved, Bucket.LOVED, note=None)
    algo.start(session, user, mine_fine, Bucket.FINE, note=None)
    algo.start(session, other, theirs, Bucket.LOVED, note=None)

    fresh = _mk_movie(session, user, tmdb_id=4, title="Fresh")
    # New LOVED ranking should only see MineLoved as a candidate (immediate finalize would need
    # zero candidates; with one candidate we expect a session).
    result = algo.start(session, user, fresh, Bucket.LOVED, note=None)
    assert result.done is False
    assert result.opponent is not None
    assert result.opponent.movie_id == mine_loved.id


# --------------------------- BeliRanking.compare loop -------------------------


def _run_full_ranking(
    session: Session,
    algo: BeliRanking,
    user: User,
    new_movie: Movie,
    bucket: Bucket,
    *,
    prefer_new_over: set[int],
) -> Ranking:
    """Drive a full rank flow. ``prefer_new_over`` names opponents the new movie should beat."""
    result = algo.start(session, user, new_movie, bucket, note=None)
    if result.done:
        assert result.ranking is not None
        return result.ranking
    assert result.session_id is not None
    assert result.opponent is not None
    session_id = result.session_id
    opponent = result.opponent
    while True:
        winner_id = new_movie.id if opponent.movie_id in prefer_new_over else opponent.movie_id
        from app.models import RankingSession

        rs = session.get(RankingSession, session_id)
        assert rs is not None
        step = algo.compare(session, rs, winner_id)  # type: ignore[arg-type]
        if step.done:
            assert step.ranking is not None
            return step.ranking
        assert step.opponent is not None
        opponent = step.opponent


def test_binary_search_places_movie_that_beats_everyone_at_top(session: Session) -> None:
    algo = BeliRanking()
    user = _mk_user(session)
    existing = [_mk_movie(session, user, tmdb_id=i, title=f"M{i}") for i in range(5)]
    for m in existing:
        algo.start(session, user, m, Bucket.LOVED, note=None)

    new_movie = _mk_movie(session, user, tmdb_id=99, title="GOAT")
    ranking = _run_full_ranking(
        session,
        algo,
        user,
        new_movie,
        Bucket.LOVED,
        prefer_new_over={m.id for m in existing},  # type: ignore[misc]
    )

    _, high = BUCKET_BANDS[Bucket.LOVED]
    assert ranking.score == round(high, 3)


def test_binary_search_places_worst_movie_at_bottom(session: Session) -> None:
    algo = BeliRanking()
    user = _mk_user(session)
    existing = [_mk_movie(session, user, tmdb_id=i, title=f"M{i}") for i in range(5)]
    for m in existing:
        algo.start(session, user, m, Bucket.LOVED, note=None)

    new_movie = _mk_movie(session, user, tmdb_id=99, title="Worst")
    ranking = _run_full_ranking(session, algo, user, new_movie, Bucket.LOVED, prefer_new_over=set())

    low, _ = BUCKET_BANDS[Bucket.LOVED]
    assert ranking.score == round(low, 3)


def test_binary_search_places_middle_movie_correctly(session: Session) -> None:
    """Given 4 existing loved movies, place a new one that beats the bottom 2 but loses to the top 2."""
    algo = BeliRanking()
    user = _mk_user(session)
    existing = [_mk_movie(session, user, tmdb_id=i, title=f"M{i}") for i in range(4)]
    for m in existing:
        algo.start(session, user, m, Bucket.LOVED, note=None)

    # Establish an ordering M0 > M1 > M2 > M3 by ranking them into the bucket in that order,
    # then re-rank each so scores reflect that order. In empty->1 land they land at midpoint;
    # subsequent rankings need proper compares. We'll do it directly: use algo but drive compares.

    # Easier: create rankings manually with known scores.
    session.exec(select(Ranking))  # ensure model loaded
    # Wipe existing rankings for these movies and craft direct rows.
    from datetime import datetime, timedelta

    for r in session.exec(select(Ranking)).all():
        session.delete(r)
    session.commit()
    base = datetime.now()
    for i, m in enumerate(existing):
        # Descending scores 9.5, 8.5, 7.5, 6.8 all inside LOVED.
        score = [9.5, 8.5, 7.5, 6.8][i]
        session.add(Ranking(movie_id=m.id, bucket=Bucket.LOVED, score=score, created_at=base + timedelta(seconds=i)))  # type: ignore[arg-type]
    session.commit()

    new_movie = _mk_movie(session, user, tmdb_id=99, title="Mid")
    # New movie should beat M2 and M3, lose to M0 and M1 → land at position 2 out of 5 total.
    prefer_new_over = {existing[2].id, existing[3].id}
    ranking = _run_full_ranking(
        session,
        algo,
        user,
        new_movie,
        Bucket.LOVED,
        prefer_new_over=prefer_new_over,  # type: ignore[misc]
    )

    expected = score_for_position(position=2, total=5, bucket=Bucket.LOVED)
    assert ranking.score == expected


def test_re_ranking_same_movie_excludes_itself_from_candidates(session: Session) -> None:
    algo = BeliRanking()
    user = _mk_user(session)
    a = _mk_movie(session, user, tmdb_id=1, title="A")
    b = _mk_movie(session, user, tmdb_id=2, title="B")
    algo.start(session, user, a, Bucket.LOVED, note=None)
    algo.start(session, user, b, Bucket.FINE, note=None)

    # Re-rank A. Only A is in LOVED; without excluding itself, it'd binary-search against itself.
    result = algo.start(session, user, a, Bucket.LOVED, note=None)
    # With no other LOVED movies (A excluded), it should finalize immediately at the midpoint.
    assert result.done is True
    assert result.ranking is not None
    low, high = BUCKET_BANDS[Bucket.LOVED]
    assert result.ranking.score == round((low + high) / 2, 3)


def test_compare_with_invalid_winner_id_raises(session: Session) -> None:
    import pytest
    from fastapi import HTTPException

    algo = BeliRanking()
    user = _mk_user(session)
    a = _mk_movie(session, user, tmdb_id=1, title="A")
    b = _mk_movie(session, user, tmdb_id=2, title="B")
    algo.start(session, user, a, Bucket.LOVED, note=None)
    result = algo.start(session, user, b, Bucket.LOVED, note=None)
    assert result.session_id is not None

    from app.models import RankingSession

    rs = session.get(RankingSession, result.session_id)
    assert rs is not None

    with pytest.raises(HTTPException) as exc:
        algo.compare(session, rs, winner_movie_id=99999)
    assert exc.value.status_code == 400


def test_binary_search_bounded_by_ceil_log2(session: Session) -> None:
    """A bucket of size N should never require more than ceil(log2(N+1)) comparisons."""
    import math

    algo = BeliRanking()
    user = _mk_user(session)
    n = 15
    existing = [_mk_movie(session, user, tmdb_id=i, title=f"M{i}") for i in range(n)]
    # Manually seed rankings with distinct decreasing scores.
    from datetime import datetime, timedelta

    base = datetime.now()
    low, high = BUCKET_BANDS[Bucket.LOVED]
    for i, m in enumerate(existing):
        score = round(high - i * (high - low) / (n - 1), 3)
        session.add(Ranking(movie_id=m.id, bucket=Bucket.LOVED, score=score, created_at=base + timedelta(seconds=i)))  # type: ignore[arg-type]
    session.commit()

    new_movie = _mk_movie(session, user, tmdb_id=100, title="New")
    result = algo.start(session, user, new_movie, Bucket.LOVED, note=None)
    assert result.session_id is not None
    session_id = result.session_id
    steps = 0
    from app.models import RankingSession

    while True:
        rs = session.get(RankingSession, session_id)
        if rs is None:
            break
        opponent_id = rs.candidate_ids[(rs.lo + rs.hi) // 2]
        # Losing every comparison drives the worst case.
        step = algo.compare(session, rs, winner_movie_id=opponent_id)
        steps += 1
        if step.done:
            break

    max_expected = math.ceil(math.log2(n + 1))
    assert steps <= max_expected, f"took {steps} comparisons for n={n}, expected <= {max_expected}"
