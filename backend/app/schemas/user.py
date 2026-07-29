from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=100)
    display_name: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    identifier: str  # email or username
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    bio: str
    avatar_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfile(UserOut):
    ranked_count: int
    want_to_watch_count: int
    followers_count: int
    following_count: int
    is_following: bool = False


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    bio: str | None = Field(default=None, max_length=280)
    avatar_url: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
