# Deploying the muvi backend (Render + Turso, always-free)

The API runs on **Render.com**'s free web-service tier and reads/writes a hosted-SQLite database
on **Turso** (libSQL). Both have permanent free tiers — no billing card required — as long as
you stay inside the free quotas.

Render free plan quirks to be aware of:

- Service spins down after ~15 minutes of inactivity. First request after that pays a ~30s
  cold-start; subsequent requests are fast.
- Filesystem is ephemeral (wiped on every deploy). All persistent state lives in Turso.

## 1. Create the Turso database

```bash
brew install tursodatabase/tap/turso
turso auth signup     # first-time only
turso db create muvi
turso db show muvi --url
turso db tokens create muvi
```

You'll configure these as **two separate values**:

```
DATABASE_URL      sqlite+libsql://<host>?secure=true
TURSO_AUTH_TOKEN  <token>
```

`<host>` is the hostname from `db show --url` with the `libsql://` prefix dropped.

The token is deliberately *not* part of the connection string. Connection URLs get echoed into
logs and tracebacks, and a Turso token grants full database access. (A token embedded in the URL
query as `?authToken=…` is still accepted as a fallback — see `engine_args` in
[`app/db.py`](./app/db.py) — but the separate variable is preferred.)

## 2. Deploy the API on Render

1. Sign in at https://render.com with the GitHub account that owns this repo and connect it.
2. **New +** → **Blueprint** → pick this repo. Render reads
   [`backend/render.yaml`](./render.yaml) and provisions one free web service.
3. When Render prompts for secrets, paste:
   - `TMDB_API_KEY` — your TMDB v3 API key.
   - `DATABASE_URL` — the `sqlite+libsql://<host>?secure=true` string from step 1.
   - `TURSO_AUTH_TOKEN` — the token from step 1.
   - (`JWT_SECRET` is generated automatically.)
4. Click **Apply**. First build takes ~4 minutes; watch the deploy log until it says "Live".

Your API is now at `https://muvi-backend.onrender.com` (or whatever name Render assigned;
check the dashboard). Sanity check:

```bash
curl https://<your-service>.onrender.com/health
# {"status":"ok"}
```

Interactive docs at `https://<your-service>.onrender.com/docs`.

## Redeploying after code changes

Render auto-deploys on every push to the tracked branch. To force one from the dashboard:
**Manual Deploy** → **Deploy latest commit**.

## Point the iOS app at prod

In `ios/Muvi/App/AppConfig.swift`, set the release-config `defaultBaseURL` to your Render URL.
Alternatively, set `MUVI_API_BASE_URL` as an Info.plist entry (per configuration) or as a
scheme env var — see the file for the resolution order.

## Troubleshooting

**`Unauthorized: empty JWT token` on startup** — the auth token isn't reaching the driver. Check
that `TURSO_AUTH_TOKEN` is set in Render. Note that putting the token in `DATABASE_URL` alone is
not enough on its own with a stock `sqlalchemy-libsql`: that dialect forwards only a fixed
allowlist of pysqlite kwargs to `libsql.connect()` and drops `auth_token`, so the app lifts it
into `connect_args` explicitly (`engine_args` in [`app/db.py`](./app/db.py)). If you changed that
function, this is the first place to look.

**Build fails compiling `libsql-experimental` / `linker cc not found`** — the image is on a Python
version with no prebuilt libsql wheel. Wheels exist through cp313; the Dockerfile pins
`python:3.13-slim` for this reason.

**First request after idle takes ~30s** — expected on Render's free plan; the service spins down
after ~15 minutes of inactivity.

## Backups

`turso db shell muvi ".dump" > muvi-backup-$(date +%Y%m%d).sql`

Restore into a fresh DB with `turso db shell <new-db> < muvi-backup-<date>.sql`.

## Migrating from a previous Fly.io deploy

If you were on the old Fly setup, pull the SQLite file down, dump it, and import to Turso:

```bash
fly ssh console -a <old-fly-app> -C "cat /data/muvi.db" > muvi-old.db
sqlite3 muvi-old.db .dump > muvi-old.sql
turso db shell muvi < muvi-old.sql
```

Then destroy the Fly app (`fly apps destroy <old-fly-app>`) to stop any lingering charges.
