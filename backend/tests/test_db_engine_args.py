"""Engine wiring for local SQLite vs. Turso/libSQL.

Regression coverage for a production failure: sqlalchemy-libsql only forwards a fixed allowlist
of pysqlite kwargs to libsql.connect(), and `auth_token` is not on it. A token left in the URL
query string was silently dropped, so every connection died with
`Unauthorized: empty JWT token`.
"""

import pytest
from sqlmodel import create_engine

from app.db import engine_args, pool_options

TOKEN = "eyJhbGciOi.FAKE-PAYLOAD_123.signature"


def test_local_sqlite_gets_check_same_thread() -> None:
    url, args = engine_args("sqlite:///./muvi.db")
    assert url == "sqlite:///./muvi.db"
    assert args == {"check_same_thread": False}


def test_local_sqlite_memory_is_unchanged() -> None:
    url, args = engine_args("sqlite:///:memory:")
    assert url == "sqlite:///:memory:"
    assert args["check_same_thread"] is False


def test_libsql_token_in_query_is_lifted_into_connect_args() -> None:
    url, args = engine_args(f"sqlite+libsql://db.turso.io?authToken={TOKEN}&secure=true")
    assert args["auth_token"] == TOKEN, "token must reach libsql.connect() as a kwarg"


def test_libsql_token_is_stripped_from_the_url() -> None:
    """Connection URLs end up in logs and tracebacks; the token must not ride along."""
    url, _ = engine_args(f"sqlite+libsql://db.turso.io?authToken={TOKEN}&secure=true")
    assert TOKEN not in url
    assert "authToken" not in url


def test_libsql_preserves_secure_flag() -> None:
    """`secure` selects https over http inside the dialect — it has to survive the rewrite."""
    url, _ = engine_args(f"sqlite+libsql://db.turso.io?authToken={TOKEN}&secure=true")
    assert "secure=true" in url
    assert url.startswith("sqlite+libsql://db.turso.io")


def test_libsql_accepts_snake_case_token_key() -> None:
    url, args = engine_args(f"sqlite+libsql://db.turso.io?auth_token={TOKEN}&secure=true")
    assert args["auth_token"] == TOKEN
    assert TOKEN not in url


def test_explicit_token_argument_wins_over_url_query() -> None:
    _, args = engine_args(
        f"sqlite+libsql://db.turso.io?authToken={TOKEN}&secure=true",
        auth_token="from-env-var",
    )
    assert args["auth_token"] == "from-env-var"


def test_explicit_token_works_when_url_has_none() -> None:
    url, args = engine_args("sqlite+libsql://db.turso.io?secure=true", auth_token=TOKEN)
    assert args["auth_token"] == TOKEN
    assert TOKEN not in url


def test_libsql_without_any_token_omits_auth_token() -> None:
    """No token configured should not send auth_token='' — let the driver's default surface."""
    _, args = engine_args("sqlite+libsql://db.turso.io?secure=true")
    assert "auth_token" not in args


def test_libsql_does_not_get_check_same_thread() -> None:
    """check_same_thread is a local-SQLite concern; libSQL is a remote connection."""
    _, args = engine_args(f"sqlite+libsql://db.turso.io?authToken={TOKEN}&secure=true")
    assert "check_same_thread" not in args


# --- Pooling ------------------------------------------------------------------------------
#
# Regression coverage for the 13 Aug 2026 outage: Turso drops idle connections, SQLAlchemy kept
# handing the dead one out, and every database-backed route 500'd until the process restarted.


def test_libsql_enables_pre_ping_and_recycle() -> None:
    options = pool_options("sqlite+libsql://db.turso.io?secure=true")
    assert options["pool_pre_ping"] is True, "a dropped remote connection must be detected on checkout"
    assert options["pool_recycle"] > 0, "connections must retire before the far end drops them"


def test_local_sqlite_skips_pooling_options() -> None:
    """A local file can't go stale; a ping per checkout would be pure overhead."""
    assert pool_options("sqlite:///./muvi.db") == {}
    assert pool_options("sqlite:///:memory:") == {}


def test_bare_libsql_scheme_also_pools() -> None:
    """`_is_local_sqlite` keys off the scheme; the libsql:// form is remote too."""
    assert pool_options("libsql://db.turso.io")["pool_pre_ping"] is True


def test_pool_options_reach_the_engines_pool(tmp_path) -> None:
    """The options dict is worthless if create_engine drops it, so assert on a real pool.

    Uses the plain sqlite dialect: `sqlalchemy-libsql` ships only in the [turso] extra that the
    production image installs, so a libsql URL can't be opened in a bare dev environment. What's
    under test here is that the kwargs survive the call, which is dialect-independent.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'plumbing.db'}", **pool_options("sqlite+libsql://db.turso.io"))
    assert engine.pool._pre_ping is True
    assert engine.pool._recycle == 300


def test_real_libsql_engine_pre_pings() -> None:
    """The same assertion against the actual dialect, where it's installed — production, and any
    dev environment with the [turso] extra. Skipped rather than faked when it isn't."""
    pytest.importorskip("sqlalchemy_libsql", reason="[turso] extra not installed")
    url, connect_args = engine_args("sqlite+libsql://db.turso.io?secure=true", auth_token=TOKEN)
    engine = create_engine(url, connect_args=connect_args, **pool_options(url))
    assert engine.pool._pre_ping is True


def test_engine_built_for_local_sqlite_does_not_pre_ping(tmp_path) -> None:
    url, connect_args = engine_args(f"sqlite:///{tmp_path / 'local.db'}")
    engine = create_engine(url, connect_args=connect_args, **pool_options(url))
    assert getattr(engine.pool, "_pre_ping", False) is False
