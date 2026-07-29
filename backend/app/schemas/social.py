from datetime import datetime

from pydantic import BaseModel

from app.models.rank import Tier
from app.schemas.movie import MovieOut
from app.schemas.user import UserOut


class FeedItem(BaseModel):
    id: int
    user: UserOut
    movie: MovieOut
    tier: Tier
    score: float
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}
