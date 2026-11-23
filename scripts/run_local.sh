#!/usr/bin/env bash
# Local, Docker-free demo: single service + SQLite (or Supabase if configured).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL="$ROOT/.local"
VENV="$LOCAL/venv"
DATA="$LOCAL/data"
LOGS="$LOCAL/logs"
PIDS="$LOCAL/pids"
mkdir -p "$DATA" "$LOGS" "$PIDS" "$DATA/media"

# Carga variables de entorno desde .env si existe (no se sube a GitHub)
if [ -f "$ROOT/.env" ]; then
  set -a
  . "$ROOT/.env"
  set +a
fi

if [ "${1:-}" = "--fresh" ]; then
  "$ROOT/scripts/stop_local.sh" >/dev/null 2>&1 || true
  rm -f "$DATA"/*.db
  shift
fi

# Si se configura SUPABASE_DB_PASSWORD, usa Supabase PostgreSQL; si no, SQLite local.
# Fuerza SQLite con USE_LOCAL_DB=1 (útil sin red o para pruebas offline).
SUPABASE_DB_URL=""
if [ -n "${SUPABASE_DB_PASSWORD:-}" ] && [ "${USE_LOCAL_DB:-0}" != "1" ]; then
  SUPABASE_DB_URL="postgresql+asyncpg://postgres:${SUPABASE_DB_PASSWORD}@db.yeaylufnjeyiutyxqict.supabase.co:5432/postgres"
fi

# En modo local/offline, desactiva también Supabase (DB y Storage).
if [ "${USE_LOCAL_DB:-0}" = "1" ]; then
  SUPABASE_DB_PASSWORD=""
  SUPABASE_URL=""
  SUPABASE_ANON_KEY=""
  SUPABASE_SERVICE_ROLE_KEY=""
fi

PYTHON="${PYTHON:-$VENV/bin/python}"
if [ ! -x "$PYTHON" ]; then
  echo "Creando venv local en $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q \
    -r "$ROOT/services/app/requirements.txt" \
    aiosqlite
  PYTHON="$VENV/bin/python"
fi

if ! "$PYTHON" -c "import aiosqlite" >/dev/null 2>&1; then
  "$PYTHON" -m pip install -q aiosqlite
fi

if ! "$PYTHON" -c "import multipart" >/dev/null 2>&1; then
  "$PYTHON" -m pip install -q \
    -r "$ROOT/services/app/requirements.txt"
fi

export PYTHONPATH="$ROOT/libs"

if [ ! -f "$ROOT/frontend/dist/index.html" ]; then
  echo "Construyendo frontend…"
  (cd "$ROOT/frontend" && npm ci && npm run build)
fi

start() {
  local name="$1" workdir="$2" port="$3"
  shift 3
  local log="$LOGS/$name.log"
  (
    cd "$workdir"
    nohup env "$@" "$PYTHON" -m uvicorn app.main:app \
      --host 127.0.0.1 --port "$port" >"$log" 2>&1 &
    echo $! >"$PIDS/$name.pid"
  )
  echo "  $name -> http://127.0.0.1:$port (log $log)"
}

http_ok() {
  "$PYTHON" -c \
    'import sys,urllib.request; sys.exit(0 if urllib.request.urlopen(sys.argv[1], timeout=3).status==200 else 1)' \
    "$1" >/dev/null 2>&1
}

wait_http() {
  local url="$1" name="$2"
  for _ in $(seq 1 60); do
    if http_ok "$url"; then
      echo "  $name listo"
      return 0
    fi
    sleep 1
  done
  echo "ERROR: $name no responde ($url). Revisa $LOGS/$name.log" >&2
  return 1
}

echo "Arrancando servicio único themis-app…"
start themis-app "$ROOT/services/app" 8000 \
  SERVICE_NAME=themis-app \
  DATABASE_URL="${SUPABASE_DB_URL:-sqlite+aiosqlite:///$DATA/themis.db}" \
  MEDIA_DIR="$DATA/media" \
  IMAGE_MAX_BYTES=5242880 \
  INVOICE_MAX_BYTES=10485760 \
  SUPABASE_URL="${SUPABASE_URL:-}" \
  SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-}" \
  SUPABASE_SERVICE_ROLE_KEY="${SUPABASE_SERVICE_ROLE_KEY:-}" \
  SUPABASE_BUCKET_PRODUCT_IMAGES="${SUPABASE_BUCKET_PRODUCT_IMAGES:-product-images}" \
  SUPABASE_BUCKET_INVOICES="${SUPABASE_BUCKET_INVOICES:-sales-invoices}" \
  SUPABASE_DB_PASSWORD="${SUPABASE_DB_PASSWORD:-}" \
  DB_SCHEMA=themis \
  LOG_LEVEL=INFO

echo "Esperando health checks…"
wait_http http://127.0.0.1:8000/health themis-app

if [ "${SEED:-1}" = "1" ]; then
  echo
  "$PYTHON" "$ROOT/scripts/seed_demo_inventory.py"
fi

echo
echo "Themis disponible en http://localhost:8000"
echo "Logs: $LOGS"
echo "Parar: scripts/stop_local.sh"
