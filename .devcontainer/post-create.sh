#!/usr/bin/env bash
# One-time setup when the codespace is created: dependencies, database, demo data, web build.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> System libraries for report-card PDFs (WeasyPrint)"
# The base image ships a Yarn apt source whose signing key has expired; we don't use it.
sudo rm -f /etc/apt/sources.list.d/yarn.list
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core postgresql-client >/dev/null

echo "==> Backend"
pip install --quiet --user uv
UV="python -m uv"   # works even when ~/.local/bin is not on PATH
cd backend
if [ ! -f .env ]; then
  cp .env.example .env
  # Fresh random secret per codespace; DB/Redis URLs come from the container environment.
  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(python -c 'import secrets;print(secrets.token_urlsafe(48))')|" .env
  sed -i '/^DATABASE_URL=/d;/^MIGRATION_DATABASE_URL=/d;/^REDIS_URL=/d' .env
fi
$UV sync --python 3.12 --extra pdf

echo "==> Waiting for Postgres"
until pg_isready -h postgres -U vidya_owner >/dev/null 2>&1; do sleep 1; done
$UV run alembic upgrade head
$UV run python -m app.seed || true   # skips if the demo school already exists

echo "==> Web"
cd ../web
npm ci --no-audit --no-fund
npm run build

echo "==> Ready. The app starts automatically (post-start.sh)."
