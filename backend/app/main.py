from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.config import get_settings
from app.db import init_db
from app.routes import auth as auth_routes
from app.routes import library as library_routes
from app.routes import movies as movies_routes
from app.routes import rank as rank_routes
from app.routes import settings as settings_routes
from app.routes import tmdb as tmdb_routes


def _version() -> str:
    """The version from pyproject.toml, read off the installed distribution.

    Declared in one place on purpose. It used to be hardcoded here as well, and the two copies
    duly drifted — pyproject said one thing while /health and /openapi.json reported another.

    Falls back rather than raising: an uninstalled source checkout is a development situation, and
    taking the whole app down over a version string would be a poor trade. The sentinel is
    obviously wrong so it can't be mistaken for a real release.
    """
    try:
        return installed_version("muvi-backend")
    except PackageNotFoundError:
        return "0.0.0+unknown"


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    yield


app = FastAPI(title="muvi", version=_version(), lifespan=lifespan)

# The library response is a long, highly repetitive JSON array — a full library easily runs to
# tens of KB uncompressed, and it's re-fetched on every app open and after every mutation.
# Compressing it cuts outbound bandwidth (which Render meters) several-fold and noticeably
# speeds up loads on cellular. 1 KB threshold leaves small responses alone.
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(auth_routes.router)
app.include_router(tmdb_routes.router)
app.include_router(rank_routes.router)
app.include_router(library_routes.router)
app.include_router(movies_routes.router)
app.include_router(settings_routes.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe, and a way to ask an instance which build it's running.

    Render polls this (see healthCheckPath in render.yaml). The commit is reported so a deploy
    can be confirmed from outside: a change with no observable behaviour is otherwise impossible
    to verify against a live service. "unknown" off-platform, where Render sets no such variable.

    The SHA is safe to expose — the repository is public. Reconsider if that ever changes.
    """
    return {
        "status": "ok",
        "version": app.version,
        "commit": get_settings().render_git_commit or "unknown",
    }
