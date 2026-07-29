"""Beli-style pairwise ranking: pick a tier (loved/liked/disliked), then binary-insert
the new movie into that tier's list via a series of "which was better?" duels.
Scores are floats in [0, 10], evenly re-spaced within a tier band after every insert
so ordering stays precise and unbounded in depth.
"""

import math

from sqlalchemy.orm import Session

from app.models.movie import Movie
from app.models.rank import Rank, RankingSession, Tier
from app.models.user import User

TIER_BANDS: dict[Tier, tuple[float, float]] = {
    Tier.LOVED: (10.0, 7.0),
    Tier.LIKED: (6.9, 4.0),
    Tier.DISLIKED: (3.9, 0.0),
}


def _tier_ranks_desc(db: Session, user_id: int, tier: Tier, exclude_rank_id: int | None = None) -> list[Rank]:
    q = db.query(Rank).filter(Rank.user_id == user_id, Rank.tier == tier)
    if exclude_rank_id is not None:
        q = q.filter(Rank.id != exclude_rank_id)
    return q.order_by(Rank.score.desc()).all()


def _rebalance_tier(tier: Tier, ranks_desc_ordered: list[Rank]) -> None:
    if not ranks_desc_ordered:
        return
    top, bottom = TIER_BANDS[tier]
    span = top - bottom
    n = len(ranks_desc_ordered)
    for i, r in enumerate(ranks_desc_ordered):
        r.score = round(top - (i + 0.5) * span / n, 3)


def comparisons_estimate(n_existing: int) -> int:
    if n_existing <= 0:
        return 0
    return max(1, math.ceil(math.log2(n_existing + 1)))


def _finalize(
    db: Session,
    user: User,
    movie: Movie,
    tier: Tier,
    note: str,
    existing_ranks_desc: list[Rank],
    insert_index: int,
) -> Rank:
    rank = db.query(Rank).filter(Rank.user_id == user.id, Rank.movie_id == movie.id).one_or_none()
    old_tier = None
    if rank is None:
        rank = Rank(user_id=user.id, movie_id=movie.id, tier=tier, note=note, score=0.0)
        db.add(rank)
        db.flush()
    else:
        old_tier = rank.tier
        rank.tier = tier
        rank.note = note
        db.flush()

    insert_index = max(0, min(insert_index, len(existing_ranks_desc)))
    new_order = existing_ranks_desc[:insert_index] + [rank] + existing_ranks_desc[insert_index:]
    _rebalance_tier(tier, new_order)

    if old_tier is not None and old_tier != tier:
        remaining = _tier_ranks_desc(db, user.id, old_tier, exclude_rank_id=rank.id)
        _rebalance_tier(old_tier, remaining)

    db.commit()
    db.refresh(rank)
    return rank


def start_session(db: Session, user: User, movie: Movie, tier: Tier, note: str) -> dict:
    existing_rank = db.query(Rank).filter(Rank.user_id == user.id, Rank.movie_id == movie.id).one_or_none()
    existing = _tier_ranks_desc(db, user.id, tier, exclude_rank_id=existing_rank.id if existing_rank else None)

    if not existing:
        rank = _finalize(db, user, movie, tier, note, existing, insert_index=0)
        return {"done": True, "result": rank, "session_id": 0}

    lo, hi = 0, len(existing) - 1
    session = RankingSession(
        user_id=user.id,
        movie_id=movie.id,
        tier=tier,
        note=note,
        candidate_rank_ids=",".join(str(r.id) for r in existing),
        lo=lo,
        hi=hi,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    mid = (lo + hi) // 2
    return {
        "done": False,
        "session_id": session.id,
        "comparison_movie": existing[mid].movie,
        "total_comparisons_estimate": comparisons_estimate(len(existing)),
        "comparisons_made": 0,
    }


def answer_session(db: Session, user: User, session: RankingSession, winner: str) -> dict:
    rank_ids = [int(x) for x in session.candidate_rank_ids.split(",") if x]
    ranks = [db.get(Rank, rid) for rid in rank_ids]

    lo, hi = session.lo, session.hi
    mid = (lo + hi) // 2
    comparisons_made = comparisons_estimate(len(ranks)) - comparisons_estimate(hi - lo + 1)

    if winner == "new":
        hi = mid - 1
    elif winner == "existing":
        lo = mid + 1
    else:
        raise ValueError("winner must be 'new' or 'existing'")

    if lo > hi:
        movie = db.get(Movie, session.movie_id)
        rank = _finalize(db, user, movie, session.tier, session.note, ranks, insert_index=lo)
        db.delete(session)
        db.commit()
        return {"done": True, "result": rank, "session_id": 0}

    session.lo, session.hi = lo, hi
    db.commit()

    mid = (lo + hi) // 2
    return {
        "done": False,
        "session_id": session.id,
        "comparison_movie": ranks[mid].movie,
        "total_comparisons_estimate": comparisons_estimate(len(ranks)),
        "comparisons_made": comparisons_made + 1,
    }
