from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.rank import Rank
from app.models.social import Follow
from app.models.user import User
from app.schemas.social import FeedItem

router = APIRouter(prefix="/api/feed", tags=["feed"])


@router.get("", response_model=list[FeedItem])
def get_feed(
    limit: int = Query(default=30, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    following_ids = [f.followee_id for f in db.query(Follow).filter(Follow.follower_id == current_user.id).all()]
    if not following_ids:
        return []
    ranks = db.query(Rank).filter(Rank.user_id.in_(following_ids)).order_by(Rank.created_at.desc()).limit(limit).all()
    return [
        FeedItem(
            id=r.id,
            user=r.user,
            movie=r.movie,
            tier=r.tier,
            score=r.score,
            note=r.note,
            created_at=r.created_at,
        )
        for r in ranks
    ]
