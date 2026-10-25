#!/usr/bin/env bash
# Runs every time the codespace starts: launch the API and the web app in the background.
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p .devcontainer/logs
# Always use the image's system Python, even if a virtualenv is active in this shell.
unset VIRTUAL_ENV
SYS_PY=/usr/local/bin/python3
[ -x "$SYS_PY" ] || SYS_PY=/usr/bin/python3
UV="$SYS_PY -m uv"

until pg_isready -h postgres -U vidya_owner >/dev/null 2>&1; do sleep 1; done
(cd backend && $UV run alembic upgrade head >/dev/null)

pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next start" 2>/dev/null || true

(cd backend && nohup $UV run uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../.devcontainer/logs/api.log 2>&1 &)
# Start the web app only once the API answers, so the first page load never fails.
for _ in $(seq 60); do curl -sf http://localhost:8000/health >/dev/null && break; sleep 1; done
(cd web && nohup npm start -- -p 3000 > ../.devcontainer/logs/web.log 2>&1 &)

echo "VidyaTrack is starting: open the 'Ports' tab and click the globe icon next to port 3000."
echo "Demo logins: principal 9000000002, OTP 123456 (see README)."
