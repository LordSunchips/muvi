# Deploying muvi backend to Fly.io

This spins up a small VM running the FastAPI app with SQLite on a persistent Fly volume.

## Prerequisites

- Install the Fly CLI (`brew install flyctl`) and sign up: `fly auth signup`.
- A TMDB API key and a JWT signing secret (any long random string).
- Docker installed locally is **not required** — Fly builds the image remotely by default.

## First-time deploy

Pick a globally-unique app name (Fly enforces uniqueness). Replace `<APP>` and `<REGION>` (see
`fly platform regions`; `iad`, `sea`, `sjc` are common) below.

```bash
cd backend

# Edit fly.toml: change `app = "muvi-backend"` to `app = "<APP>"`.

fly launch --no-deploy --copy-config --name <APP>
fly volumes create muvi_data --size 1 --region <REGION>
fly secrets set TMDB_API_KEY=your_tmdb_key \
                JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
fly deploy
```

Your API is now at `https://<APP>.fly.dev`. Sanity check:

```bash
curl https://<APP>.fly.dev/health
# {"status":"ok"}
```

Open the docs at `https://<APP>.fly.dev/docs`.

## Redeploying after code changes

```bash
cd backend && fly deploy
```

## Cost

The `fly.toml` here uses one shared-cpu-1x / 256 MB machine and a 1 GB volume. With
`auto_stop_machines = "stop"` set, the VM sleeps when idle and cold-starts on the next request
(~1–2 seconds). Fits inside Fly's minimal allowance for a personal app; watch billing at
https://fly.io/dashboard.

## Backups

The SQLite DB lives at `/data/muvi.db` on the volume. Quick backup:

```bash
fly ssh console -C "cat /data/muvi.db" > muvi-backup-$(date +%Y%m%d).db
```

## Point the iOS app at prod

In Xcode, edit `ios/Muvi/App/AppConfig.swift` and set the base URL to your Fly URL, or set the
`MUVI_API_BASE_URL` build setting on the scheme (see the file for details).
