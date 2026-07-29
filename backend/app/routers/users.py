from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.rank import Rank
from app.models.social import Follow
from app.models.user import User
from app.models.want_to_watch import WantToWatch
from app.schemas.user import UserOut, UserProfile, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def _to_profile(db: Session, user: User, viewer: User) -> UserProfile:
    ranked_count = db.query(Rank).filter(Rank.user_id == user.id).count()
    wtw_count = db.query(WantToWatch).filter(WantToWatch.user_id == user.id).count()
    followers_count = db.query(Follow).filter(Follow.followee_id == user.id).count()
    following_count = db.query(Follow).filter(Follow.follower_id == user.id).count()
    is_following = (
        db.query(Follow).filter(Follow.follower_id == viewer.id, Follow.followee_id == user.id).first() is not None
    )
    return UserProfile(
        **UserOut.model_validate(user).model_dump(),
        ranked_count=ranked_count,
        want_to_watch_count=wtw_count,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following,
    )


@router.get("/search", response_model=list[UserOut])
def search_users(
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    like = f"%{q}%"
    users = db.query(User).filter((User.username.ilike(like)) | (User.display_name.ilike(like))).limit(25).all()
    return users


@router.get("/{user_id}", response_model=UserProfile)
def get_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return _to_profile(db, user, current_user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.bio is not None:
        current_user.bio = payload.bio
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot follow yourself")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    existing = db.query(Follow).filter(Follow.follower_id == current_user.id, Follow.followee_id == user_id).first()
    if existing:
        return
    db.add(Follow(follower_id=current_user.id, followee_id=user_id))
    db.commit()


@router.delete("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Follow).filter(Follow.follower_id == current_user.id, Follow.followee_id == user_id).first()
    if existing:
        db.delete(existing)
        db.commit()


@router.get("/{user_id}/followers", response_model=list[UserOut])
def list_followers(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    follows = db.query(Follow).filter(Follow.followee_id == user_id).all()
    return [db.get(User, f.follower_id) for f in follows]


@router.get("/{user_id}/following", response_model=list[UserOut])
def list_following(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    follows = db.query(Follow).filter(Follow.follower_id == user_id).all()
    return [db.get(User, f.followee_id) for f in follows]
