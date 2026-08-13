from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tmdb_api_key: str = ""
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 1 week
    database_url: str = "sqlite:///./muvi.db"
    # Turso/libSQL auth token. Kept separate from database_url so the credential stays out of
    # connection strings (which land in logs and tracebacks). A token embedded in database_url's
    # query string still works as a fallback — see app.db.engine_args.
    turso_auth_token: str = ""
    # Set by Render at runtime (all service types, Docker included) to the deployed commit SHA.
    # Surfaced by /health so a running instance can be asked which build it is — otherwise the
    # only way to tell whether a deploy landed is the dashboard, and a change with no observable
    # behaviour (a timezone fix on a UTC host, say) can't be confirmed from outside at all.
    # Empty off-platform, which is the local-development case.
    render_git_commit: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
