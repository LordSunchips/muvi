from collections.abc import Iterator
from uuid import uuid4

from sqlalchemy import event, inspect, text
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


def pool_options(database_url: str) -> dict:
    """Connection-pool settings, which only a *remote* database needs.

    Turso is reached over the network and the far end drops idle connections. By default
    SQLAlchemy doesn't notice: it hands the dead connection to the next request, that query
    fails, and — because the connection is returned to the pool rather than discarded — every
    subsequent request fails too. Only a process restart clears it.

    That took production down on 13 Aug 2026. Every database-backed route returned 500 while
    /health, which touches no database, stayed green; restarting the service fixed it instantly
    with the same credentials and the same schema, which is what ruled out the alternatives.

    The free plan had been hiding this. Spinning down after 15 minutes idle meant no pool ever
    lived long enough to go stale — moving to Starter for the cold starts kept the process alive
    and let the latent bug surface.

    - ``pool_pre_ping`` checks liveness on checkout and transparently replaces a dead connection.
    - ``pool_recycle`` retires connections before the far end is likely to have dropped them,
      so the pre-ping check rarely has to do the replacing.

    Local SQLite is a file opened in-process: nothing to go stale, and a per-checkout ping would
    be pure overhead.
    """
    if _is_local_sqlite(database_url):
        return {}
    return {"pool_pre_ping": True, "pool_recycle": 300}


_url, connect_args = engine_args(settings.database_url, settings.turso_auth_token)
engine = create_engine(_url, echo=False, connect_args=connect_args, **pool_options(settings.database_url))


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record) -> None:  # noqa: ARG001
    if _is_local_sqlite(settings.database_url):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _add_users_public_id() -> None:
    """Add ``users.public_id`` to a database created before that column existed.

    There's no migration tool here: ``init_db`` calls ``create_all``, which creates missing
    tables but never alters existing ones. Production already has a ``users`` table from before
    public_id, so without this the column would never appear there and every request would fail
    on the missing attribute.

    Idempotent — it inspects first and returns immediately once the column is present, which is
    also the fresh-database case (``create_all`` will have just made it). Safe on a single
    instance, which is what the Render service runs; concurrent instances could race the ALTER.

    This is a stopgap for one column. A second schema change should bring in Alembic instead.
    """
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    if any(column["name"] == "public_id" for column in inspector.get_columns("users")):
        return

    with engine.begin() as conn:
        # SQLite can't ADD COLUMN with a UNIQUE constraint, so the column goes on bare and the
        # uniqueness comes from the index below — the same index create_all would have made.
        conn.execute(text("ALTER TABLE users ADD COLUMN public_id VARCHAR"))
        for (user_id,) in conn.execute(text("SELECT id FROM users")).fetchall():
            conn.execute(
                text("UPDATE users SET public_id = :public_id WHERE id = :user_id"),
                {"public_id": uuid4().hex, "user_id": user_id},
            )
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_public_id ON users (public_id)"))


def init_db() -> None:
    # Import models so SQLModel.metadata is populated before create_all.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _add_users_public_id()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
