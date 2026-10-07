#!/bin/sh
# Bring Cite back after a sandbox restart: Postgres, API, then the Vite client.
set -eu
cd /workspace

export PATH="/opt/pg16/bin:${PATH}"

if [ -x /opt/pg16/bin/pg_isready ]; then
  if ! /opt/pg16/bin/pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1; then
    if [ -d /opt/pg16/data ]; then
      /opt/pg16/bin/pg_ctl -D /opt/pg16/data -l /opt/pg16/pg.log start
    fi
  fi
fi

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://cite@127.0.0.1:5432/cite}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
export CHAT_MODEL="${CHAT_MODEL:-qwen2.5:7b-instruct}"
export EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"
export SESSION_SECRET="${SESSION_SECRET:-dev-only-change-me}"
export FILE_STORAGE_DIR="${FILE_STORAGE_DIR:-/workspace/data/files}"
export COOKIE_SECURE="${COOKIE_SECURE:-false}"
mkdir -p "$FILE_STORAGE_DIR"

if [ -x /workspace/backend/.venv/bin/alembic ]; then
  (cd /workspace/backend && .venv/bin/alembic upgrade head) || true
fi

SOCK=/tmp/cite-api.sock
export CITE_API_SOCKET="$SOCK"

# A TCP API steals the preview (it is discovered ahead of the web app).
# Keep the API on a unix socket so the preview has only the web app to show.
if [ -x /workspace/backend/.venv/bin/uvicorn ]; then
  api_code=$(curl -s -o /dev/null -w "%{http_code}" --unix-socket "$SOCK" --max-time 1 http://localhost/auth/me || true)
  if [ "$api_code" != "401" ] && [ "$api_code" != "200" ]; then
    for p in /proc/[0-9]*; do
      cmd=$(tr "\0" " " 2>/dev/null < "$p/cmdline" || true)
      case "$cmd" in
        *uvicorn*) kill "$(basename "$p")" 2>/dev/null || true ;;
      esac
    done
    rm -f "$SOCK"
    (
      cd /workspace/backend
      nohup .venv/bin/uvicorn app.main:app --uds "$SOCK" > /tmp/cite-api.log 2>&1 &
    )
  fi
fi

# Drop any leftover TCP listener even if the socket is already healthy.
for p in /proc/[0-9]*; do
  cmd=$(tr "\0" " " 2>/dev/null < "$p/cmdline" || true)
  case "$cmd" in
    *"--port 8000"*) kill "$(basename "$p")" 2>/dev/null || true ;;
  esac
done

if ! curl -sf -o /dev/null --max-time 1 http://127.0.0.1:8080/; then
  cd /workspace
  nohup npm run dev > /tmp/cite-web.log 2>&1 &
fi

# Tell the preview which server is the app, once it is listening.
if curl -sf -o /dev/null --max-time 1 http://127.0.0.1:6015/__control/healthz; then
  curl -sf -o /dev/null --max-time 2 -X POST http://127.0.0.1:6015/__control/target \
    -H 'content-type: application/json' -d '{"port":8080}' || true
fi

exit 0
