#!/usr/bin/env python3
"""Seed the demo inventory through the public API.

The catalog is populated dynamically (no hardcoded catalog logic in services):
this script only replays the stock list provided by the store. It creates each
product, then sets the stock with an adjustment. Products at zero trigger a
stock.depleted event on purpose.

Usage:
    BASE_URL=http://127.0.0.1:8000 python3 scripts/seed_demo_inventory.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
COLOR = "Estándar"

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "product-images"
MANIFEST_PATH = ASSETS_DIR / "manifest.json"
IMAGE_MAP: dict[tuple[str, str], Path] = {}
if MANIFEST_PATH.exists():
    for entry in json.loads(MANIFEST_PATH.read_text(encoding="utf-8")):
        if entry.get("file"):
            IMAGE_MAP[(entry["brand"], entry["model"])] = ASSETS_DIR / f"{entry['file']}.webp"

def usd(value: float) -> float:
    return round(value * 1.08, 2)

# (brand, model, ram_gb, storage_gb, category, cost_price, price, quantity, note)
DEMO_INVENTORY: list[
    tuple[str, str, int, int, str, float, float, int, Optional[str]]
] = [
    # TECNO
    ("Tecno", "Spark Go3", 4, 128, "phone", 85, 129, 1, None),
    ("Tecno", "Camon 50 Ultra 5G", 9, 256, "phone", 330, 449, 1, None),
    ("Tecno", "Pova 8 Pro 5G", 12, 512, "phone", 330, 449, 1, None),
    # INFINIX
    ("Infinix", "Smart 20", 4, 64, "phone", 70, 99, 3, None),
    ("Infinix", "Hot 70", 4, 128, "phone", 95, 139, 2, None),
    ("Infinix", "Hot 70", 4, 256, "phone", 110, 159, 0, None),
    ("Infinix", "Hot 70", 8, 256, "phone", 125, 179, 1, None),
    ("Infinix", "Hot 70 Pro 5G", 8, 256, "phone", 160, 229, 1, None),
    # SAMSUNG
    ("Samsung", "Galaxy A06", 4, 64, "phone", 110, 159, 2, None),
    ("Samsung", "Galaxy A07", 6, 128, "phone", 130, 189, 0, None),
    ("Samsung", "Galaxy A07s", 4, 64, "phone", 105, 149, 2, None),
    ("Samsung", "Galaxy A08", 4, 64, "phone", 115, 165, 2, None),
    ("Samsung", "Galaxy A16", 4, 128, "phone", 140, 199, 1, None),
    ("Samsung", "Galaxy A17", 6, 128, "phone", 155, 219, 1, None),
    ("Samsung", "Galaxy A17", 8, 256, "phone", 180, 249, 2, None),
    ("Samsung", "Galaxy A27 5G", 8, 256, "phone", 230, 319, 2, None),
    ("Samsung", "Galaxy A57 5G", 8, 256, "phone", 350, 479, 2, None),
    ("GPS", "TAG2", 0, 0, "accessory", 10, 19, 3, None),
    # REDMI
    ("Redmi", "A7", 3, 64, "phone", 60, 89, 1, None),
    ("Redmi", "A7 Pro", 4, 64, "phone", 70, 99, 0, None),
    ("Redmi", "A7 Pro", 4, 128, "phone", 80, 119, 1, None),
    ("Redmi", "15C", 4, 256, "phone", 110, 159, 1, None),
    ("Redmi", "15C", 8, 256, "phone", 130, 189, 2, None),
    ("Redmi", "17", 4, 128, "phone", 115, 165, 1, None),
    ("Redmi", "17", 4, 256, "phone", 130, 185, 2, None),
    ("Redmi", "17", 6, 256, "phone", 145, 205, 1, None),
    ("Redmi", "Note 17", 6, 128, "phone", 160, 229, 2, None),
    ("Redmi", "Note 17", 6, 256, "phone", 175, 249, 2, None),
    ("Redmi", "Note 17 5G", 8, 512, "phone", 250, 349, 1, None),
    ("Redmi", "Note 17 Pro Max 5G", 8, 512, "phone", 300, 419, 2, None),
    ("Redmi", "Note 17 Pro Max", 8, 256, "phone", 260, 359, 1, None),
    # HONOR
    ("Honor", "Play 10", 3, 64, "phone", 70, 99, 2, None),
    ("Honor", "Play 10", 4, 128, "phone", 85, 119, 1, None),
    ("Honor", "T10", 4, 128, "phone", 95, 139, 2, None),
    ("Honor", "X7E", 6, 256, "phone", 140, 199, 1, None),
    # OTROS
    ("UPS", "Mini UPS", 0, 0, "accessory", 20, 35, 0, None),
    ("Motorola", "Moto G06", 4, 64, "phone", 85, 119, 2, None),
    ("Motorola", "Moto G06", 4, 128, "phone", 95, 139, 1, None),
    ("Oukitel", "C67", 4, 128, "phone", 85, 129, 2, None),
    ("Oukitel", "G3", 4, 128, "phone", 75, 109, 1, None),
    ("Oukitel", "C17", 4, 64, "phone", 65, 95, 2, None),
    ("Oukitel", "C17", 4, 128, "phone", 75, 109, 2, None),
    ("Oukitel", "C72", 4, 128, "phone", 90, 129, 2, None),
    ("Oukitel", "WP56", 8, 256, "phone", 150, 219, 1, None),
    ("Alcatel", "3", 3, 64, "phone", 45, 69, 2, "Inventario inicial: 1 equipo defectuoso"),
    ("Alcatel", "A33", 4, 64, "phone", 55, 79, 2, None),
    ("Tablet", "M10", 3, 64, "tablet", 60, 89, 0, None),
    ("Amazon", "Fire TV Stick 4K Max", 0, 0, "accessory", 40, 65, 1, None),
]


def slug(value: str) -> str:
    cleaned = "".join(
        character if character.isalnum() else "-" for character in value.upper()
    )
    return "-".join(part for part in cleaned.split("-") if part)


def make_sku(brand: str, model: str, ram: int, storage: int) -> str:
    parts = [slug(brand), slug(model)]
    if ram:
        parts.append(f"{ram}G")
    if storage:
        parts.append(f"{storage}GB")
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


def wait_for_gateway(attempts: int = 60) -> None:
    for attempt in range(1, attempts + 1):
        status, _ = http("GET", "/health", timeout=5)
        if status == 200:
            return
        print(f"  esperando gateway ({attempt}/{attempts})…")
        time.sleep(1)
    raise SystemExit(f"El gateway no responde en {BASE_URL}")


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
                "note": note or "Carga inicial demo (sin stock)",
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
        {"quantity": target, "note": note or "Carga inicial demo"},
    )
    if status in (200, 201):
        return "updated"
    raise RuntimeError(f"adjustment failed ({status}): {body}")


def main() -> int:
    print(f"Sembrando inventario demo en {BASE_URL}")
    wait_for_gateway()

    created = 0
    existing = 0
    adjustments = 0
    alerts = 0
    units = 0
    errors: list[str] = []

    total = len(DEMO_INVENTORY)
    for index, (
        brand,
        model,
        ram,
        storage,
        category,
        cost_price,
        price,
        quantity,
        note,
    ) in enumerate(DEMO_INVENTORY, start=1):
        sku = make_sku(brand, model, ram, storage)
        label = (
            f"[{index:02d}/{total}] {brand} {model} {ram}/{storage}GB "
            f"· {quantity} uds · {price:.0f} €"
        )
        print(label)

        status, body = http(
            "POST",
            "/api/catalog/products",
            {
                "sku": sku,
                "brand": brand,
                "model": model,
                "ram_gb": ram,
                "storage_gb": storage,
                "color": COLOR,
                "category": category,
                "cost_price_eur": cost_price,
                "price_eur": price,
                "cost_price_usd": usd(cost_price),
                "price_usd": usd(price),
                "threshold": 0,
            },
        )

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

        image_path = IMAGE_MAP.get((brand, model))
        product_data = body if status == 201 and isinstance(body, dict) else found
        has_image = bool(product_data.get("image_updated_at")) if isinstance(product_data, dict) else False
        if image_path and image_path.is_file() and not has_image:
            try:
                boundary = "----ThemisFormBoundary" + uuid.uuid4().hex
                parts = [
                    f"--{boundary}",
                    f'Content-Disposition: form-data; name="file"; filename="{image_path.name}"',
                    "Content-Type: image/webp",
                    "",
                ]
                crlf = b"\r\n"
                boundary_bytes = boundary.encode("ascii")
                parts = [
                    b"--" + boundary_bytes,
                    f'Content-Disposition: form-data; name="file"; filename="{image_path.name}"'.encode("utf-8"),
                    b"Content-Type: image/webp",
                    b"",
                ]
                body_bytes = (
                    crlf.join(parts)
                    + crlf
                    + image_path.read_bytes()
                    + crlf
                    + b"--" + boundary_bytes + b"--"
                    + crlf
                )
                img_req = urllib.request.Request(
                    f"{BASE_URL}/api/catalog/products/{product_id}/image",
                    data=body_bytes,
                    method="POST",
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                )
                with urllib.request.urlopen(img_req, timeout=30) as img_response:
                    if img_response.status not in (200, 201):
                        errors.append(f"{sku}: image upload HTTP {img_response.status}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{sku}: image upload failed: {exc}")

        stock = wait_for_stock(product_id)
        if stock is None:
            errors.append(f"{sku}: el stock no se creó a tiempo")
            continue

        try:
            outcome = set_stock(product_id, quantity, stock, note)
        except RuntimeError as exc:
            errors.append(f"{sku}: {exc}")
            continue

        if outcome in {"updated", "alert_triggered"}:
            adjustments += 1
        if outcome == "alert_triggered":
            alerts += 1
        units += quantity

    time.sleep(2)
    status, dashboard = http("GET", "/api/dashboard")
    status_logs, logs = http("GET", "/api/notifications?limit=200")

    print("\n=== Resumen ===")
    print(f"Productos en la lista : {total}")
    print(f"Creados               : {created}")
    print(f"Ya existentes         : {existing}")
    print(f"Ajustes de stock      : {adjustments}")
    print(f"Unidades totales      : {units}")
    print(f"Alertas disparadas    : {alerts}")
    if status == 200 and isinstance(dashboard, dict):
        print(
            f"Dashboard             : {dashboard['count']} productos, "
            f"{dashboard['low_stock_count']} sin/bajo stock"
        )
    if status_logs == 200 and isinstance(logs, list):
        print(f"Notificaciones        : {len(logs)} registros")

    if errors:
        print("\nErrores:")
        for error in errors:
            print(f"  - {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
