"""The `users.public_id` backfill, exercised against a database that predates the column.

Production's `users` table was created before `public_id` existed. `create_all` only creates
missing tables, never alters existing ones, so the column arrives via `_add_users_public_id`.
If that path is broken the deploy takes the API down: every authenticated request touches
`User.public_id`.
"""

from sqlalchemy import inspect, text
from sqlmodel import create_engine

import app.db as db_module


def _legacy_users_table(engine) -> None:
    """A `users` table shaped the way it was before public_id, with two rows in it."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE users ("
                " id INTEGER NOT NULL PRIMARY KEY,"
                " email VARCHAR NOT NULL,"
                " password_hash VARCHAR NOT NULL,"
                " created_at DATETIME NOT NULL)"
            )
        )
        for user_id, email in ((1, "a@example.com"), (2, "b@example.com")):
            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, created_at)"
                    " VALUES (:id, :email, 'hash', '2026-01-01 00:00:00')"
                ),
                {"id": user_id, "email": email},
            )


def test_backfill_adds_column_and_fills_existing_rows(tmp_path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}", connect_args={"check_same_thread": False})
    _legacy_users_table(engine)
    assert not any(c["name"] == "public_id" for c in inspect(engine).get_columns("users"))

    monkeypatch.setattr(db_module, "engine", engine)
    db_module._add_users_public_id()

    assert any(c["name"] == "public_id" for c in inspect(engine).get_columns("users"))
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, public_id FROM users ORDER BY id")).fetchall()
    public_ids = [public_id for _, public_id in rows]
    assert all(public_ids), "every pre-existing row must get a public_id"
    assert len(set(public_ids)) == len(public_ids), "backfilled ids must be distinct"


def test_backfill_is_idempotent(tmp_path, monkeypatch) -> None:
    """It runs on every startup, so a second pass must not error or churn the values."""
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}", connect_args={"check_same_thread": False})
    _legacy_users_table(engine)
    monkeypatch.setattr(db_module, "engine", engine)

    db_module._add_users_public_id()
    with engine.begin() as conn:
        first = conn.execute(text("SELECT id, public_id FROM users ORDER BY id")).fetchall()

    db_module._add_users_public_id()
    with engine.begin() as conn:
        second = conn.execute(text("SELECT id, public_id FROM users ORDER BY id")).fetchall()

    assert first == second


def test_backfilled_column_rejects_duplicates(tmp_path, monkeypatch) -> None:
    """The unique index has to survive the ALTER, since SQLite can't add a UNIQUE column."""
    import pytest
    import sqlalchemy.exc

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}", connect_args={"check_same_thread": False})
    _legacy_users_table(engine)
    monkeypatch.setattr(db_module, "engine", engine)
    db_module._add_users_public_id()

    with engine.begin() as conn:
        existing = conn.execute(text("SELECT public_id FROM users WHERE id = 1")).scalar_one()

    with pytest.raises(sqlalchemy.exc.IntegrityError), engine.begin() as conn:
        conn.execute(text("UPDATE users SET public_id = :pid WHERE id = 2"), {"pid": existing})


def test_backfill_noop_on_fresh_database(tmp_path, monkeypatch) -> None:
    """No users table yet: create_all owns that case, so the backfill must simply stand down."""
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db_module, "engine", engine)
    db_module._add_users_public_id()
    assert "users" not in inspect(engine).get_table_names()
