#!/usr/bin/env python3
"""Siembra el catálogo y el stock inicial a través de la API pública.

Carga los productos y precios que nos proporcionó la tienda, ajusta el stock
de cada uno y dispara las alertas de stock cuando corresponde.

Usage:
    BASE_URL=https://console-themis-b6t5p.sprites.app python3 scripts/seed_demo_inventory.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
import urllib
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
COLOR = "Estándar"

# (brand, model, ram_gb, ram_virtual_gb, storage_gb, category, pago_usd,
#  bcv_usd, cashea_usd, camera, quantity, note)
CATALOG: list[dict[str, Any]] = [
    # ---------------- TECNO ----------------
    {"brand": "Tecno", "model": "Spark Go 3", "ram": 4, "virtual": 4,
     "storage": 64, "category": "phone", "pago": 118, "bcv": 143, "cashea": 157,
     "camera": "13+0.3MP", "qty": 1, "note": None},
    {"brand": "Tecno", "model": "Camon 50 Ultra", "ram": 8, "virtual": 8,
     "storage": 256, "category": "phone", "pago": 427, "bcv": 518, "cashea": 570,
     "camera": "50MP", "qty": 1, "note": None},
    {"brand": "Tecno", "model": "Pova 8 5G Lamborghini", "ram": 12, "virtual": 12,
     "storage": 256, "category": "phone", "pago": 462, "bcv": 561, "cashea": 617,
     "camera": "50MP", "qty": 1, "note": None},
    # ---------------- INFINIX ----------------
    {"brand": "Infinix", "model": "Smart 20", "ram": 4, "virtual": 4,
     "storage": 64, "category": "phone", "pago": 139, "bcv": 162, "cashea": 178,
     "camera": "8+2MP", "qty": 3, "note": None},
    {"brand": "Infinix", "model": "Hot 70", "ram": 4, "virtual": 4,
     "storage": 128, "category": "phone", "pago": 150, "bcv": 181, "cashea": 199,
     "camera": "50+2MP", "qty": 2, "note": None},
    {"brand": "Infinix", "model": "Hot 70", "ram": 4, "virtual": 4,
     "storage": 256, "category": "phone", "pago": 218, "bcv": 265, "cashea": 291,
     "camera": "50+2MP", "qty": 0, "note": None},
    {"brand": "Infinix", "model": "Hot 70", "ram": 8, "virtual": 8,
     "storage": 256, "category": "phone", "pago": 248, "bcv": 299, "cashea": 329,
     "camera": "50+2MP", "qty": 1, "note": None},
    {"brand": "Infinix", "model": "Hot 70 Pro 5G", "ram": 8, "virtual": 8,
     "storage": 256, "category": "phone", "pago": 332, "bcv": 403, "cashea": 443,
     "camera": "50+8MP", "qty": 1, "note": None},
    # ---------------- SAMSUNG ----------------
    {"brand": "Samsung", "model": "Galaxy A06", "ram": 4, "virtual": 4,
     "storage": 64, "category": "phone", "pago": 132, "bcv": 160, "cashea": 176,
     "camera": "50+2MP", "qty": 2, "note": None},
    {"brand": "Samsung", "model": "Galaxy A07", "ram": 6, "virtual": 6,
     "storage": 128, "category": "phone", "pago": 167, "bcv": 203, "cashea": 223,
     "camera": "50+2MP", "qty": 0, "note": None},
    {"brand": "Samsung", "model": "Galaxy A07s", "ram": 4, "virtual": 4,
     "storage": 64, "category": "phone", "pago": 141, "bcv": 171, "cashea": 188,
     "camera": "50+2MP", "qty": 2, "note": None},
    {"brand": "Samsung", "model": "Galaxy A08", "ram": 4, "virtual": 4,
     "storage": 64, "category": "phone", "pago": 176, "bcv": 214, "cashea": 235,
     "camera": "50+2MP", "qty": 2, "note": None},
    {"brand": "Samsung", "model": "Galaxy A16", "ram": 4, "virtual": 4,
     "storage": 128, "category": "phone", "pago": 162, "bcv": 196, "cashea": 216,
     "camera": "50+5+2MP", "qty": 1, "note": None},
    {"brand": "Samsung", "model": "Galaxy A17", "ram": 6, "virtual": 6,
     "storage": 128, "category": "phone", "pago": 225, "bcv": 274, "cashea": 301,
     "camera": "50+5+2MP", "qty": 1, "note": None},
    {"brand": "Samsung", "model": "Galaxy A17", "ram": 8, "virtual": 8,
     "storage": 256, "category": "phone", "pago": 316, "bcv": 383, "cashea": 421,
     "camera": "50+5+5MP", "qty": 2, "note": None},
    {"brand": "Samsung", "model": "Galaxy A27 5G", "ram": 8, "virtual": 8,
     "storage": 256, "category": "phone", "pago": 390, "bcv": 474, "cashea": 521,
     "camera": "50+5+2MP", "qty": 2, "note": None},
    {"brand": "Samsung", "model": "Galaxy A57 5G", "ram": 8, "virtual": 8,
     "storage": 256, "category": "phone", "pago": 487, "bcv": 592, "cashea": 651,
     "camera": "50+13+5MP", "qty": 2, "note": None},
    # ---------------- REDMI ----------------
    {"brand": "Redmi", "model": "A7", "ram": 3, "virtual": 3,
     "storage": 64, "category": "phone", "pago": 112, "bcv": 136, "cashea": 150,
     "camera": "13+2MP", "qty": 1, "note": None},
    {"brand": "Redmi", "model": "A7 Pro", "ram": 4, "virtual": 4,
     "storage": 64, "category": "phone", "pago": 120, "bcv": 145, "cashea": 160,
     "camera": "50+2MP", "qty": 0, "note": None},
    {"brand": "Redmi", "model": "A7 Pro", "ram": 4, "virtual": 4,
     "storage": 128, "category": "phone", "pago": 139, "bcv": 168, "cashea": 185,
     "camera": "50+2MP", "qty": 1, "note": None},
    {"brand": "Redmi", "model": "15C", "ram": 4, "virtual": 4,
     "storage": 256, "category": "phone", "pago": 150, "bcv": 181, "cashea": 199,
     "camera": "50+2MP", "qty": 1, "note": None},
    {"brand": "Redmi", "model": "15C", "ram": 8, "virtual": 8,
     "storage": 256, "category": "phone", "pago": 164, "bcv": 195, "cashea": 215,
     "camera": "50+2MP", "qty": 2, "note": None},
    {"brand": "Redmi", "model": "17", "ram": 4, "virtual": 4,
     "storage": 128, "category": "phone", "pago": 170, "bcv": 207, "cashea": 228,
     "camera": "50+2MP", "qty": 1, "note": None},
    {"brand": "Redmi", "model": "17", "ram": 4, "virtual": 4,
     "storage": 256, "category": "phone", "pago": 205, "bcv": 250, "cashea": 275,
     "camera": "50+2MP", "qty": 2, "note": None},
    {"brand": "Redmi", "model": "17", "ram": 6, "virtual": 6,
     "storage": 256, "category": "phone", "pago": 233, "bcv": 283, "cashea": 311,
     "camera": "50+2MP", "qty": 1, "note": None},
    {"brand": "Redmi", "model": "Note 17", "ram": 6, "virtual": 6,
     "storage": 128, "category": "phone", "pago": 220, "bcv": 267, "cashea": 294,
     "camera": "50+2MP", "qty": 2, "note": None},
    {"brand": "Redmi", "model": "Note 17", "ram": 6, "virtual": 6,
     "storage": 256, "category": "phone", "pago": 234, "bcv": 284, "cashea": 312,
     "camera": "50+2MP", "qty": 2, "note": None},
    {"brand": "Redmi", "model": "Note 17 Pro 5G", "ram": 8, "virtual": 8,
     "storage": 512, "category": "phone", "pago": 408, "bcv": 494, "cashea": 543,
     "camera": "50+8MP", "qty": 1, "note": None},
    {"brand": "Redmi", "model": "Note 17 Pro Max", "ram": 8, "virtual": 8,
     "storage": 512, "category": "phone", "pago": 480, "bcv": 583, "cashea": 641,
     "camera": "50+8MP", "qty": 2, "note": None},
    {"brand": "Redmi", "model": "Note 17 Pro Max", "ram": 8, "virtual": 8,
     "storage": 256, "category": "phone", "pago": 434, "bcv": 527, "cashea": 580,
     "camera": "50+8MP", "qty": 1, "note": None},
    # ---------------- HONOR ----------------
    {"brand": "Honor", "model": "Play 10", "ram": 3, "virtual": 3,
     "storage": 64, "category": "phone", "pago": 110, "bcv": 134, "cashea": 147,
     "camera": "13+2MP", "qty": 2, "note": None},
    {"brand": "Honor", "model": "Play 10", "ram": 4, "virtual": 4,
     "storage": 128, "category": "phone", "pago": 124, "bcv": 151, "cashea": 166,
     "camera": "13+2MP", "qty": 1, "note": None},
    {"brand": "Honor", "model": "Choice T10", "ram": 4, "virtual": 4,
     "storage": 128, "category": "phone", "pago": 132, "bcv": 160, "cashea": 176,
     "camera": "13MP", "qty": 2, "note": None},
    {"brand": "Honor", "model": "X7E", "ram": 6, "virtual": 6,
     "storage": 256, "category": "phone", "pago": 255, "bcv": 310, "cashea": 341,
     "camera": "50+2MP", "qty": 1, "note": None},
    # ---------------- MOTOROLA ----------------
    {"brand": "Motorola", "model": "G06", "ram": 4, "virtual": 8,
     "storage": 64, "category": "phone", "pago": 124, "bcv": 151, "cashea": 166,
     "camera": "50+2MP", "qty": 2, "note": None},
    {"brand": "Motorola", "model": "G06", "ram": 4, "virtual": 8,
     "storage": 128, "category": "phone", "pago": 147, "bcv": 179, "cashea": 197,
     "camera": "50+2MP", "qty": 1, "note": None},
    # ---------------- Oukitel ----------------
    {"brand": "Oukitel", "model": "C67", "ram": 4, "virtual": 8,
     "storage": 128, "category": "phone", "pago": 134, "bcv": 162, "cashea": 178,
     "camera": "64+2+0.3MP", "qty": 2, "note": None},
    {"brand": "Oukitel", "model": "G3", "ram": 4, "virtual": 12,
     "storage": 128, "category": "phone", "pago": 130, "bcv": 158, "cashea": 174,
     "camera": "13+0.3MP", "qty": 1, "note": None},
    {"brand": "Oukitel", "model": "C17", "ram": 4, "virtual": 8,
     "storage": 64, "category": "phone", "pago": 99, "bcv": 121, "cashea": 133,
     "camera": "13+0.3MP", "qty": 2, "note": None},
    {"brand": "Oukitel", "model": "C17", "ram": 4, "virtual": 8,
     "storage": 128, "category": "phone", "pago": 133, "bcv": 162, "cashea": 178,
     "camera": "13+0.3MP", "qty": 2, "note": None},
    {"brand": "Oukitel", "model": "C72", "ram": 4, "virtual": 8,
     "storage": 128, "category": "phone", "pago": 144, "bcv": 175, "cashea": 193,
     "camera": "64+2+0.3MP", "qty": 2, "note": None},
    {"brand": "Oukitel", "model": "WP56", "ram": 8, "virtual": 16,
     "storage": 256, "category": "phone", "pago": 280, "bcv": 339, "cashea": 373,
     "camera": "108+2MP", "qty": 1, "note": None},
    # ---------------- ALCATEL ----------------
    {"brand": "Alcatel", "model": "3 2026", "ram": 3, "virtual": 3,
     "storage": 64, "category": "phone", "pago": 91, "bcv": 109, "cashea": 120,
     "camera": "8+2MP", "qty": 2,
     "note": "Inventario inicial: 1 equipo defectuoso"},
    {"brand": "Alcatel", "model": "A33", "ram": 4, "virtual": 4,
     "storage": 64, "category": "phone", "pago": 99, "bcv": 121, "cashea": 133,
     "camera": "8+2+0.3MP", "qty": 2, "note": None},
    # ---------------- TABLET ----------------
    {"brand": "Pritom", "model": "M10 Kids", "ram": 3, "virtual": 5,
     "storage": 64, "category": "tablet", "pago": 109, "bcv": 132, "cashea": 145,
     "camera": "8MP", "qty": 0, "note": None},
    # ---------------- ACCESORIOS (sin precio asignado) ----------------
    {"brand": "GPS", "model": "TAG2", "ram": 0, "virtual": 0,
     "storage": 0, "category": "accessory", "pago": 0, "bcv": 0, "cashea": 0,
     "camera": None, "qty": 3, "note": None},
    {"brand": "Amazon", "model": "Fire TV Stick 4K Max", "ram": 0, "virtual": 0,
     "storage": 0, "category": "accessory", "pago": 0, "bcv": 0, "cashea": 0,
     "camera": None, "qty": 1, "note": None},
]


def slug(value: str) -> str:
    cleaned = "".join(
        character if character.isalnum() else "-" for character in value.upper()
    )
    return "-".join(part for part in cleaned.split("-") if part)


def make_sku(entry: dict[str, Any]) -> str:
    parts = [slug(entry["brand"]), slug(entry["model"])]
    if entry["ram"]:
        parts.append(f"{entry['ram']}G")
    if entry["virtual"]:
        parts.append(f"+{entry['virtual']}G")
    if entry["storage"]:
        parts.append(f"{entry['storage']}GB")
    parts.append(slug(COLOR))
    return "-".join(parts)[:64]


def http(
    method: str, path: str, payload: Optional[dict[str, Any]] = None, timeout: float = 30.0
) -> tuple[int, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    request = urllib.request.Request(
        f"{BASE_URL}{path}", data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw
    except urllib.error.URLError as exc:
        return 0, str(exc)


def wait_for_api(attempts: int = 60) -> None:
    for attempt in range(1, attempts + 1):
        status, _ = http("GET", "/health", timeout=5)
        if status == 200:
            return
        print(f"  esperando API ({attempt}/{attempts})…")
        time.sleep(1)
    raise SystemExit(f"La API no responde en {BASE_URL}")


def find_existing(sku: str) -> Optional[dict[str, Any]]:
    query = urllib.parse.urlencode({"search": sku, "limit": 50})
    status, data = http("GET", f"/api/catalog/products?{query}")
    if status == 200 and isinstance(data, list):
        for product in data:
            if product.get("sku") == sku:
                return product
    return None


def wait_for_stock(product_id: str, timeout: float = 30.0) -> Optional[dict[str, Any]]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, data = http("GET", f"/api/inventory/stock/{product_id}")
        if status == 200 and isinstance(data, dict):
            return data
        time.sleep(0.4)
    return None


def set_stock(
    product_id: str, target: int, stock: dict[str, Any], note: Optional[str]
) -> str:
    current = int(stock.get("quantity", 0))
    if target == 0:
        if stock.get("alert_state") == "depleted":
            return "already_depleted"
        status, body = http(
            "POST",
            f"/api/inventory/stock/{product_id}/adjustments",
            {
                "quantity": 0,
                "note": note or "Carga inicial (sin stock)",
            },
        )
        if status in (200, 201):
            return "alert_triggered"
        raise RuntimeError(f"adjustment failed ({status}): {body}")

    if current == target:
        return "unchanged"

    status, body = http(
        "POST",
        f"/api/inventory/stock/{product_id}/adjustments",
        {"quantity": target, "note": note or "Carga inicial"},
    )
    if status in (200, 201):
        return "updated"
    raise RuntimeError(f"adjustment failed ({status}): {body}")


def main() -> int:
    print(f"Sembrando catálogo y stock en {BASE_URL}")
    wait_for_api()

    created = 0
    existing = 0
    adjustments = 0
    alerts = 0
    units = 0
    errors: list[str] = []

    total = len(CATALOG)
    for index, entry in enumerate(CATALOG, start=1):
        sku = make_sku(entry)
        label = (
            f"[{index:02d}/{total}] {entry['brand']} {entry['model']} "
            f"{entry['ram']}/{entry['storage']}GB · {entry['qty']} uds · "
            f"${entry['pago']}"
        )
        print(label)

        payload = {
            "sku": sku,
            "brand": entry["brand"],
            "model": entry["model"],
            "ram_gb": entry["ram"],
            "ram_virtual_gb": entry["virtual"],
            "storage_gb": entry["storage"],
            "color": COLOR,
            "category": entry["category"],
            "price_usd": entry["pago"],
            "price_bcv_usd": entry["bcv"],
            "price_cashea_usd": entry["cashea"],
            "camera": entry["camera"],
            "threshold": 0,
        }

        status, body = http("POST", "/api/catalog/products", payload)

        if status == 201 and isinstance(body, dict):
            product_id = body["id"]
            created += 1
        elif status == 409:
            found = find_existing(sku)
            if not found:
                errors.append(f"{sku}: 409 pero no se encontró en el catálogo")
                continue
            product_id = found["id"]
            existing += 1
        else:
            errors.append(f"{sku}: create failed ({status}): {body}")
            continue

        stock = wait_for_stock(product_id)
        if stock is None:
            errors.append(f"{sku}: el stock no se creó a tiempo")
            continue

        try:
            outcome = set_stock(product_id, entry["qty"], stock, entry["note"])
        except RuntimeError as exc:
            errors.append(f"{sku}: {exc}")
            continue

        if outcome in {"updated", "alert_triggered"}:
            adjustments += 1
        if outcome == "alert_triggered":
            alerts += 1
        units += entry["qty"]

    time.sleep(2)
    status, dashboard = http("GET", "/api/dashboard")

    print("\n=== Resumen ===")
    print(f"Entradas en la lista : {total}")
    print(f"Productos creados    : {created}")
    print(f"Ya existentes        : {existing}")
    print(f"Ajustes de stock     : {adjustments}")
    print(f"Unidades totales     : {units}")
    print(f"Alertas disparadas   : {alerts}")
    if status == 200 and isinstance(dashboard, dict):
        print(
            f"Dashboard            : {dashboard['count']} productos, "
            f"{dashboard['low_stock_count']} sin/bajo stock, factor BCV "
            f"{dashboard.get('bcv_factor', 0):.2f}"
        )

    if errors:
        print("\nErrores:")
        for error in errors:
            print(f"  - {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
