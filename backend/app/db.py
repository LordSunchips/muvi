from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()


def _is_local_sqlite(url: str) -> bool:
    """True for on-disk / in-memory SQLite. Turso's `sqlite+libsql://` and `libsql://` are
    remote and shouldn't share sqlite's connect_args or pragma handling."""
    return url.startswith("sqlite:") and "libsql" not in url


connect_args = {"check_same_thread": False} if _is_local_sqlite(settings.database_url) else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record) -> None:  # noqa: ARG001
    if _is_local_sqlite(settings.database_url):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    # Import models so SQLModel.metadata is populated before create_all.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
