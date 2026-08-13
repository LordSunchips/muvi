from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.db import get_session
from app.models import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(
    auto_error=True,
    description="Paste the access_token returned by /auth/signup or /auth/login.",
)

SessionDep = Annotated[Session, Depends(get_session)]


def current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> User:
    public_id = decode_access_token(credentials.credentials)
    if public_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # Looked up by public_id, not primary key: a deleted account's rowid gets handed to the next
    # signup, and `session.get(User, id)` would resolve an old token onto that new user.
    user = session.exec(select(User).where(User.public_id == public_id)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
