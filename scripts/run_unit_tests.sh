#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -x "$ROOT/.local/venv/bin/python" ]; then
  PYTHON="$ROOT/.local/venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi
case "$PYTHON" in
  */*) PYTHON="$(cd "$(dirname "$PYTHON")" && pwd)/$(basename "$PYTHON")" ;;
esac
export PYTHONPATH="$ROOT/libs"

run() {
  local service="$1"
  local label="$2"
  echo "==> $label"
  (cd "$ROOT/services/$service" && "$PYTHON" -m unittest discover -s tests -v)
}

run catalog "catalog-service schemas"
run inventory "inventory-service transitions"
run notification "notification-service formatting"
run sales "sales-service schemas"
