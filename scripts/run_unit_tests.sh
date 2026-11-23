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

echo "==> themis-app tests"
(cd "$ROOT/services/app" && "$PYTHON" -m unittest discover -s tests -v)
