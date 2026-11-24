#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SKU="DEMO-$(date +%s)"

json_field() {
  python3 -c 'import sys,json; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"
}

echo "==> Creando producto dinámico $SKU"
PRODUCT=$(curl -sS -f -X POST "$BASE_URL/api/catalog/products" \
  -H 'Content-Type: application/json' \
  -H "X-Correlation-ID: demo-$(date +%s)" \
  -d "{\"sku\":\"$SKU\",\"brand\":\"Apple\",\"model\":\"iPhone 15\",\"category\":\"phone\",\"ram_gb\":6,\"storage_gb\":128,\"color\":\"Negro\",\"price_usd\":1080.00,\"price_bcv_usd\":1300.00,\"price_cashea_usd\":1440.00,\"camera\":\"48MP\",\"threshold\":1}")
PRODUCT_ID=$(printf '%s' "$PRODUCT" | json_field id)
echo "product_id=$PRODUCT_ID"

echo "==> Entrada de 5 unidades"
curl -sS -f -X POST "$BASE_URL/api/inventory/stock/$PRODUCT_ID/entries" \
  -H 'Content-Type: application/json' \
  -d '{"quantity":5,"note":"Recepción demo"}' | python3 -m json.tool

echo "==> Venta de 5 unidades (cruza el umbral -> stock.depleted)"
SALE_KEY="demo-sale-$(date +%s)"
curl -sS -f -X POST "$BASE_URL/api/sales" \
  -H 'Content-Type: application/json' \
  -d "{\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":5}],\"payment_method\":\"card\",\"customer_name\":\"Cliente demo\",\"vendedor\":\"Vendedor demo\",\"idempotency_key\":\"$SALE_KEY\"}" \
  | python3 -m json.tool

echo "==> Últimas notificaciones"
curl -sS -f "$BASE_URL/api/notifications?limit=10" | python3 -m json.tool

echo "==> Resumen del dashboard"
curl -sS -f "$BASE_URL/api/dashboard" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print({k:d[k] for k in ("count","low_stock_count","total_units")})'
