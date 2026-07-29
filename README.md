# muvi

beli but for movies because i don't like letterboxd

muvi is a movie-ranking app built around Beli's core mechanic: instead of giving
a movie a star rating out of thin air, you rank it against movies you've already
watched through a series of "which was better?" duels. That head-to-head process
places it precisely in your personal list and gives it a 0–10 score.

## How it works

1. **Search** for a movie and add it to your **want-to-watch** list, or jump
   straight to ranking it if you've already seen it.
2. **Rank it**: pick a tier — *Loved it* / *Liked it* / *Didn't like it*.
3. **Duel**: you're shown a movie you've already ranked in that tier and asked
   "which was better?" A few rounds of this (binary search, so ~log₂(n)
   comparisons) place the new movie precisely among your existing rankings.
4. Your **rankings** page shows every movie you've ranked, ordered by score,
   with color-coded tiers (green/yellow/red) just like Beli.
5. **Follow friends** and see their rankings show up in your **feed**.

## Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy, SQLite, JWT auth
- **Frontend**: Node.js, React 19, TypeScript, Vite, React Router
- **Movie data**: [TMDB](https://www.themoviedb.org/) API (optional — falls
  back to a small built-in offline catalog of ~20 well-known movies if no API
  key is configured, so the app works out of the box)

## Running locally

### Backend

Requires Python 3.14+. This repo uses [uv](https://github.com/astral-sh/uv)
for dependency management, but any tool that reads `pyproject.toml` works.

```bash
cd backend
cp .env.example .env   # optionally add your TMDB_API_KEY
uv sync                # or: pip install -e .
uv run uvicorn app.main:app --reload --port 8000
```

The API is served at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`. The SQLite database (`muvi.db`) and tables are
created automatically on first run.

To search real, current movies (posters, full metadata) instead of the
offline fallback catalog, grab a free API key at
https://www.themoviedb.org/settings/api and set `TMDB_API_KEY` in `.env`.

### Frontend

Requires Node.js 18+.

```bash
cd frontend
cp .env.example .env   # points at the backend; defaults to localhost:8000
npm install
npm run dev
```

The app is served at `http://localhost:5173`.

## Project layout

```
backend/
  app/
    models/       SQLAlchemy models (User, Movie, Rank, RankingSession, Follow, WantToWatch)
    schemas/       Pydantic request/response schemas
    routers/       FastAPI route handlers (auth, movies, want-to-watch, rankings, users, feed)
    services/
      tmdb.py       TMDB search/details, with offline fallback catalog
      ranking.py    The pairwise binary-insertion ranking algorithm
    main.py         App entrypoint

frontend/
  src/
    api/            Typed fetch client
    context/         Auth context (JWT stored in localStorage)
    components/      Shared UI (ranking duel modal, movie posters, score badges, nav)
    pages/           Rankings, Search, Watchlist, Feed, Friends, Profile, Login/Register
```

## Notes on the ranking algorithm

Each tier (loved/liked/disliked) maps to a score band (10–7, 6.9–4, 3.9–0).
When you rank a new movie, the server binary-searches it into your existing
ranked list for that tier via pairwise comparisons, then evenly re-spaces
every score in the tier across its band so the ordering stays exact — no
float-precision creep no matter how many movies you rank over time.
