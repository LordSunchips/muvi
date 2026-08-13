from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import select

from app.deps import CurrentUser, SessionDep
from app.models import RankingSession, User, UserSettings
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _issue_token(user: User) -> TokenResponse:
    assert user.id is not None
    return TokenResponse(access_token=create_access_token(user.public_id), user=UserOut(id=user.id, email=user.email))


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, session: SessionDep) -> TokenResponse:
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    session.add(user)
    session.flush()
    session.add(UserSettings(user_id=user.id))
    session.commit()
    session.refresh(user)
    return _issue_token(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _issue_token(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user: CurrentUser, session: SessionDep) -> None:
    """Permanently delete the signed-in user and everything belonging to them.

    Required by App Store Guideline 5.1.1(v): an app offering account creation must let the user
    delete the account from inside the app, not just deactivate it.

    Movies, rankings and settings come along via ORM cascades declared on the relationships.
    `ranking_sessions` does not: it has no ORM relationship back to User, so SQLAlchemy won't
    cascade it, and the DB won't either on Turso — `PRAGMA foreign_keys=ON` is only issued for
    local SQLite (see `_sqlite_pragmas` in app.db), so the table's ON DELETE CASCADE never fires
    in production. Clear it explicitly, before the user goes, to avoid orphaned rows.
    """
    for rank_session in session.exec(select(RankingSession).where(RankingSession.user_id == user.id)).all():
        session.delete(rank_session)
    session.delete(user)
    session.commit()
