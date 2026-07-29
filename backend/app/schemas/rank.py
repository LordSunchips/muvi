from datetime import datetime

from pydantic import BaseModel

from app.models.rank import Tier
from app.schemas.movie import MovieOut


class RankOut(BaseModel):
    id: int
    movie: MovieOut
    tier: Tier
    score: float
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StartRankingRequest(BaseModel):
    tmdb_id: int
    tier: Tier
    note: str = ""


class RankingSessionOut(BaseModel):
    session_id: int
    done: bool
    comparison_movie: MovieOut | None = None
    result: RankOut | None = None
    total_comparisons_estimate: int = 0
    comparisons_made: int = 0


class AnswerRequest(BaseModel):
    winner: str  # "new" or "existing"
