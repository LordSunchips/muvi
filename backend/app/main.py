from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routes import auth as auth_routes
from app.routes import rank as rank_routes
from app.routes import tmdb as tmdb_routes


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    yield


app = FastAPI(title="muvi", version="0.1.0", lifespan=lifespan)

app.include_router(auth_routes.router)
app.include_router(tmdb_routes.router)
app.include_router(rank_routes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
