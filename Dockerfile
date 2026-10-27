# Deadlock Coach on a cloud host: build the site, then run the API that serves it.
#
# The host must:
# - mount a persistent volume at /data (cache, settings, parsed replays live there);
# - set COACH_PASSWORD_HASH to the output of `npm run password-hash` (login is always on);
# - route its public HTTPS address to $PORT (most hosts set PORT themselves).
# Runs as root on purpose: several hosts mount volumes owned by root, which a non-root
# app could not write to.

FROM node:24-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COACH_DATA_DIR=/data \
    COACH_REQUIRE_LOGIN=1 \
    PORT=8000
WORKDIR /app
COPY backend/pyproject.toml backend/
COPY backend/app backend/app
RUN pip install --no-cache-dir -e ./backend
COPY --from=web /app/frontend/dist frontend/dist
RUN mkdir -p /data
EXPOSE 8000
# --proxy-headers: the host ends HTTPS and forwards plain HTTP; trust its X-Forwarded-* headers.
CMD ["sh", "-c", "exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
