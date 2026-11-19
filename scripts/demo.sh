#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
SKU="DEMO-$(date +%s)"

json_field() {
  python3 -c 'import sys,json; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"
}

echo "==> Creando producto dinámico $SKU"
PRODUCT=$(curl -sS -f -X POST "$BASE_URL/api/catalog/products" \
  -H 'Content-Type: application/json' \
  -H "X-Correlation-ID: demo-$(date +%s)" \
  -d "{\"sku\":\"$SKU\",\"brand\":\"Apple\",\"model\":\"iPhone 15\",\"category\":\"phone\",\"storage_gb\":128,\"color\":\"Negro\",\"cost_price\":720.00,\"price\":999.00,\"currency\":\"EUR\",\"threshold\":1}")
PRODUCT_ID=$(printf '%s' "$PRODUCT" | json_field id)
echo "product_id=$PRODUCT_ID"

echo "==> Esperando a que inventory-service consuma product.created"
sleep 3

echo "==> Entrada de 5 unidades"
curl -sS -f -X POST "$BASE_URL/api/inventory/stock/$PRODUCT_ID/entries" \
  -H 'Content-Type: application/json' \
  -d '{"quantity":5,"note":"Recepción demo"}' | python3 -m json.tool

echo "==> Venta de 5 unidades (cruza el umbral -> stock.depleted)"
SALE_KEY="demo-sale-$(date +%s)"
curl -sS -f -X POST "$BASE_URL/api/sales" \
  -H 'Content-Type: application/json' \
  -d "{\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":5}],\"payment_method\":\"card\",\"customer_name\":\"Cliente demo\",\"idempotency_key\":\"$SALE_KEY\"}" \
  | python3 -m json.tool

echo "==> Esperando a notification-service"
sleep 3

echo "==> Últimas notificaciones"
curl -sS -f "$BASE_URL/api/notifications?limit=10" | python3 -m json.tool

echo "==> Resumen del dashboard"
curl -sS -f "$BASE_URL/api/dashboard" | python3 -c \
  'import sys,json; d=json.load(sys.stdin); print({"count": d["count"], "low_stock_count": d["low_stock_count"]})'

echo "==> Resumen de ventas"
curl -sS -f "$BASE_URL/api/sales/summary" | python3 -c \
  'import sys,json; d=json.load(sys.stdin); print({"today": d["today"], "top_products": d["top_products"]})'
