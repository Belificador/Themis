#!/usr/bin/env bash
# Local, Docker-free demo: SQLite per service + HTTP event relay.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL="$ROOT/.local"
VENV="$LOCAL/venv"
DATA="$LOCAL/data"
LOGS="$LOCAL/logs"
PIDS="$LOCAL/pids"
mkdir -p "$DATA" "$LOGS" "$PIDS" "$DATA/catalog-media" "$DATA/sales-media"

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

# Si se configura SUPABASE_DB_PASSWORD, todos los servicios usan Supabase
# PostgreSQL en lugar de SQLite local.
SUPABASE_DB_URL=""
if [ -n "${SUPABASE_DB_PASSWORD:-}" ]; then
  SUPABASE_DB_URL="postgresql+asyncpg://postgres:${SUPABASE_DB_PASSWORD}@db.yeaylufnjeyiutyxqict.supabase.co:5432/postgres"
fi

PYTHON="${PYTHON:-$VENV/bin/python}"
if [ ! -x "$PYTHON" ]; then
  echo "Creando venv local en $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q \
    -r "$ROOT/services/catalog/requirements.txt" \
    -r "$ROOT/services/sales/requirements.txt" \
    -r "$ROOT/gateway/requirements.txt" \
    aiosqlite
  PYTHON="$VENV/bin/python"
fi

if ! "$PYTHON" -c "import aiosqlite" >/dev/null 2>&1; then
  "$PYTHON" -m pip install -q aiosqlite
fi

if ! "$PYTHON" -c "import multipart" >/dev/null 2>&1; then
  "$PYTHON" -m pip install -q     -r "$ROOT/services/catalog/requirements.txt"     -r "$ROOT/services/sales/requirements.txt"     -r "$ROOT/gateway/requirements.txt"
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

echo "Arrancando event relay…"
start event-relay "$ROOT/services/event-relay" 8090 \
  SERVICE_NAME=event-relay \
  RELAY_DB="$DATA/relay.db" \
  LOG_LEVEL=INFO

echo "Arrancando microservicios…"
start catalog-service "$ROOT/services/catalog" 8001 \
  SERVICE_NAME=catalog-service \
  DATABASE_URL="${SUPABASE_DB_URL:-sqlite+aiosqlite:///$DATA/catalog.db}" \
  EVENT_BUS=http \
  EVENT_RELAY_URL=http://127.0.0.1:8090 \
  PRODUCTS_EXCHANGE=products \
  MEDIA_DIR="$DATA/catalog-media" \
  IMAGE_MAX_BYTES=5242880 \
  SUPABASE_URL="${SUPABASE_URL:-}" \
  SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-}" \
  SUPABASE_BUCKET_PRODUCT_IMAGES="${SUPABASE_BUCKET_PRODUCT_IMAGES:-product-images}" \
  SUPABASE_DB_PASSWORD="${SUPABASE_DB_PASSWORD:-}" \
  DB_SCHEMA=catalog \
  OUTBOX_INTERVAL_SECONDS=0.5 \
  LOG_LEVEL=INFO

start inventory-service "$ROOT/services/inventory" 8002 \
  SERVICE_NAME=inventory-service \
  DATABASE_URL="${SUPABASE_DB_URL:-sqlite+aiosqlite:///$DATA/inventory.db}" \
  EVENT_BUS=http \
  EVENT_RELAY_URL=http://127.0.0.1:8090 \
  PRODUCTS_EXCHANGE=products \
  STOCK_EXCHANGE=stock \
  INVENTORY_QUEUE=inventory.product_events \
  OUTBOX_INTERVAL_SECONDS=0.5 \
  LOG_LEVEL=INFO \
  SUPABASE_DB_PASSWORD="${SUPABASE_DB_PASSWORD:-}" \
  DB_SCHEMA=inventory

start notification-service "$ROOT/services/notification" 8003 \
  SERVICE_NAME=notification-service \
  DATABASE_URL="${SUPABASE_DB_URL:-sqlite+aiosqlite:///$DATA/notification.db}" \
  EVENT_BUS=http \
  EVENT_RELAY_URL=http://127.0.0.1:8090 \
  STOCK_EXCHANGE=stock \
  NOTIFICATION_QUEUE=notification.stock_events \
  DEDUPE_WINDOW_SECONDS=300 \
  MAX_ATTEMPTS=3 \
  LOG_LEVEL=INFO \
  TELEGRAM_ENABLED=true \
  TELEGRAM_BOT_TOKEN= \
  TELEGRAM_CHAT_ID= \
  WHATSAPP_ENABLED=true \
  WHATSAPP_TOKEN= \
  WHATSAPP_PHONE_NUMBER_ID= \
  WHATSAPP_RECIPIENT= \
  WHATSAPP_API_VERSION=v20.0 \
  SUPABASE_DB_PASSWORD="${SUPABASE_DB_PASSWORD:-}" \
  DB_SCHEMA=notification

start sales-service "$ROOT/services/sales" 8004 \
  SERVICE_NAME=sales-service \
  DATABASE_URL="${SUPABASE_DB_URL:-sqlite+aiosqlite:///$DATA/sales.db}" \
  CATALOG_URL=http://127.0.0.1:8001 \
  INVENTORY_URL=http://127.0.0.1:8002 \
  MEDIA_DIR="$DATA/sales-media" \
  INVOICE_MAX_BYTES=10485760 \
  SUPABASE_URL="${SUPABASE_URL:-}" \
  SUPABASE_SERVICE_ROLE_KEY="${SUPABASE_SERVICE_ROLE_KEY:-}" \
  SUPABASE_BUCKET_INVOICES="${SUPABASE_BUCKET_INVOICES:-sales-invoices}" \
  SUPABASE_DB_PASSWORD="${SUPABASE_DB_PASSWORD:-}" \
  DB_SCHEMA=sales \
  LOG_LEVEL=INFO

start api-gateway "$ROOT/gateway" 8080 \
  SERVICE_NAME=api-gateway \
  CATALOG_URL=http://127.0.0.1:8001 \
  INVENTORY_URL=http://127.0.0.1:8002 \
  NOTIFICATION_URL=http://127.0.0.1:8003 \
  SALES_URL=http://127.0.0.1:8004 \
  STATIC_DIR="$ROOT/frontend/dist" \
  LOG_LEVEL=INFO

echo "Esperando health checks…"
wait_http http://127.0.0.1:8090/health event-relay
wait_http http://127.0.0.1:8001/health catalog-service
wait_http http://127.0.0.1:8002/health inventory-service
wait_http http://127.0.0.1:8003/health notification-service
wait_http http://127.0.0.1:8004/health sales-service
wait_http http://127.0.0.1:8080/health api-gateway

if [ "${SEED:-1}" = "1" ]; then
  echo
  "$PYTHON" "$ROOT/scripts/seed_demo_inventory.py"
fi

echo
echo "Themis disponible en http://localhost:8080"
echo "Logs: $LOGS"
echo "Parar: scripts/stop_local.sh"
