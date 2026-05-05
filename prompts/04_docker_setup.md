# 04 — Containerise a Python service

## Context

Use this when you have a working FastAPI / Typer / async-worker Python
service and need a production-grade Dockerfile + compose stack. The
goal is a small, non-root image that doesn't blow up at runtime.

## Template

```
Produce a multi-stage Dockerfile and a docker-compose.yml for the
following Python service. Constraints:

  - Base image: python:3.12-slim
  - Builder stage installs build deps; runtime stage does not
  - Final image runs as a non-root user (uid >= 10000)
  - Healthcheck: HTTP GET /health expecting 200
  - No secrets baked into the image — all config via env vars
  - .dockerignore included
  - Compose stack includes the service + any sidecars it needs
    (Postgres, Redis, etc.)
  - Compose has restart: unless-stopped on every service
  - Compose volumes named (not anonymous) so they survive recreate

Service:
  - Entry point:   {python -m app | uvicorn app.main:app}
  - Required deps: {requirements.txt path}
  - Sidecars:      {redis | postgres | none}
  - Listen port:   {8080}
  - Health URL:    {GET /health}
```

## Example

A FastAPI security microservice on port 8080 that needs Redis for
rate limiting and reads `JWT_SECRET` and `REDIS_URL` from env.

## Expected Output

A Dockerfile that:
1. Uses `python:3.12-slim AS builder` then a trim runtime stage.
2. Creates `appuser` with uid 10001 and `chown`s `/app` to it.
3. Copies in `requirements.txt` first, installs, then app code (so
   layer cache works on code changes).
4. Sets `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`.
5. Defines a `HEALTHCHECK` calling `curl -f http://localhost:8080/health`.

A compose file with: `app` (build context, env_file, depends_on with
`condition: service_healthy`), `redis` (official image, named
volume), and an `app-net` network.

A `.dockerignore` excluding `.git`, `.venv`, `__pycache__`, `.env`,
`tests/`.

## Common Pitfalls

- **`COPY . .` before installing requirements.** Kills layer caching
  on every code change. Always copy `requirements.txt` first.
- **Running as root.** AI defaults to root if you don't pin a uid.
  Check `USER` is set.
- **Healthcheck without `--start-period`.** Service that takes 10s
  to boot reports unhealthy and gets restart-looped.
- **Mounting `./` into the container in compose.** Convenient in dev,
  catastrophic in prod (it shadows the image's installed deps).
  Confirm whether this is a dev-compose or a prod-compose.
- **`latest` tags on sidecars.** `redis:latest` shifts under you.
  Pin to a major: `redis:7`.
