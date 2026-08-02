from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()


def _is_local_sqlite(url: str) -> bool:
    """True for on-disk / in-memory SQLite. Turso's `sqlite+libsql://` and `libsql://` are
    remote and shouldn't share sqlite's connect_args or pragma handling."""
    return url.startswith("sqlite:") and "libsql" not in url


def _is_libsql(url: str) -> bool:
    return "libsql" in url


def engine_args(database_url: str, auth_token: str = "") -> tuple[str, dict]:
    """Resolve ``(url, connect_args)`` for ``create_engine``.

    For Turso/libSQL the auth token has to arrive as libsql.connect()'s ``auth_token``
    keyword. sqlalchemy-libsql only forwards a fixed allowlist of pysqlite kwargs (uri,
    timeout, isolation_level, detect_types, check_same_thread, cached_statements, secure)
    and ``auth_token`` is not on it — so a token left in the URL query string is silently
    dropped and every connection fails with "empty JWT token". We lift it into
    connect_args ourselves.

    The token is also stripped from the returned URL: connection URLs surface in logs and
    tracebacks, and a Turso token is a full-access credential.

    ``auth_token`` (from TURSO_AUTH_TOKEN) wins over a token embedded in the URL query, so
    the credential can be configured separately from the connection string.
    """
    if _is_local_sqlite(database_url):
        return database_url, {"check_same_thread": False}
    if not _is_libsql(database_url):
        return database_url, {}

    url = make_url(database_url)
    query = dict(url.query)
    embedded = query.pop("authToken", None) or query.pop("auth_token", None)
    token = auth_token or embedded or ""

    connect_args: dict = {}
    if token:
        connect_args["auth_token"] = token
    return url.set(query=query).render_as_string(hide_password=False), connect_args


_url, connect_args = engine_args(settings.database_url, settings.turso_auth_token)
engine = create_engine(_url, echo=False, connect_args=connect_args)


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
