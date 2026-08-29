# muvi

Beli but for movies because i don't like letterboxd.

A personal movie-ranking app: rank films using a Beli-style bucket + binary-search algorithm, log when you watched them, keep private notes.

## Repo layout

```
backend/    FastAPI + SQLite backend (auth, TMDB proxy, ranking engine)
ios/        SwiftUI iOS app (thin client)
```

## Backend quickstart

```
cd backend
uv sync                    # or: python -m venv .venv && .venv/bin/pip install -e '.[dev]'
cp .env.example .env       # then fill in TMDB_API_KEY and JWT_SECRET
uv run uvicorn app.main:app --reload
```

## iOS quickstart

Open `ios/Muvi.xcodeproj` in Xcode, pick an iOS 17+ simulator, run. The app expects the backend at `http://127.0.0.1:8000` by default.
