#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$ROOT/.local/pids"

if [ ! -d "$PID_DIR" ]; then
  echo "No hay procesos locales registrados."
  exit 0
fi

for file in "$PID_DIR"/*.pid; do
  [ -e "$file" ] || continue
  pid="$(cat "$file")"
  name="$(basename "$file" .pid)"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    echo "Parado $name (pid $pid)"
  fi
  rm -f "$file"
done
