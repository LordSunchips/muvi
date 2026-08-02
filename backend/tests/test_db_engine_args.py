"""Engine wiring for local SQLite vs. Turso/libSQL.

Regression coverage for a production failure: sqlalchemy-libsql only forwards a fixed allowlist
of pysqlite kwargs to libsql.connect(), and `auth_token` is not on it. A token left in the URL
query string was silently dropped, so every connection died with
`Unauthorized: empty JWT token`.
"""

from app.db import engine_args

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
