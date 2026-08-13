from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.db import init_db
from app.routes import auth as auth_routes
from app.routes import library as library_routes
from app.routes import movies as movies_routes
from app.routes import rank as rank_routes
from app.routes import settings as settings_routes
from app.routes import tmdb as tmdb_routes


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    yield


app = FastAPI(title="muvi", version="0.1.1", lifespan=lifespan)

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
    return {"status": "ok"}
