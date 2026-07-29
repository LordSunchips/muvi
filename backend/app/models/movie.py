from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_path: Mapped[str] = mapped_column(String(500), default="")
    backdrop_path: Mapped[str] = mapped_column(String(500), default="")
    overview: Mapped[str] = mapped_column(Text, default="")
    director: Mapped[str] = mapped_column(String(200), default="")
    runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    genres: Mapped[str] = mapped_column(String(300), default="")
