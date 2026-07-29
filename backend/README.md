# muvi backend

FastAPI + SQLite. Provides auth, a TMDB proxy, and the ranking engine.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
# edit .env to add TMDB_API_KEY and JWT_SECRET
uvicorn app.main:app --reload
```

OpenAPI docs at http://127.0.0.1:8000/docs.

## Layout

```
app/
  main.py              FastAPI app + router registration
  config.py            Settings loaded from .env
  db.py                SQLModel engine + session dependency
  models.py            User, Movie, Ranking, WatchEntry, RankingSession, UserSettings
  security.py          bcrypt + JWT helpers
  deps.py              current_user, get_session dependencies
  tmdb.py              async httpx client wrapping TMDB v3
  ranking/
    base.py            RankingAlgorithm protocol + shared types
    beli.py            Bucket + binary-search implementation
  routes/
    auth.py            signup, login
    library.py         list, add, remove movies
    rank.py            start / compare / delete rankings
    movies.py          detail (rank history + watches), watch CRUD, settings
    tmdb.py            search, movie detail, genres

tests/                 pytest suite (algorithm has the heaviest coverage)
```

## Ranking algorithm

Modular behind `RankingAlgorithm` in `app/ranking/base.py`. Only `BeliRanking` is implemented so far; the aspect-weighted variant will slot in behind the same protocol later.

Beli-style flow: user picks a sentiment bucket (`loved` / `fine` / `bad`), then binary-searches against existing ranked movies in that bucket via a series of "which was better?" comparisons. Final position maps to a 0–10 score inside the bucket's score band.
