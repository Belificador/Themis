#!/usr/bin/env python3
"""Descarga y normaliza imágenes oficiales de productos para el catálogo demo.

Lee ``assets/product-images/manifest.json`` y escribe imágenes WebP en
``assets/product-images/``. Cada entrada del manifiesto puede incluir:

- ``image_url``: URL directa de la imagen oficial.
- ``page_url``: página oficial del producto; se extrae ``og:image`` si no hay
  ``image_url`` directa.
- ``file``: nombre base del archivo de salida (sin extensión).
- ``source``: procedencia (por ejemplo "official").

Solo se guardan imágenes validadas (JPEG/PNG/WebP) y convertidas a WebP.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "assets" / "product-images" / "manifest.json"
IMAGES_DIR = ROOT / "assets" / "product-images"
MAX_EDGE = 1000
MAX_BYTES = 5 * 1024 * 1024

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "Chrome/120 Safari/537.36",
    "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
}


class OgImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.og_image: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            props = dict(attrs)
            if props.get("property") == "og:image" or props.get("name") == "twitter:image":
                content = props.get("content")
                if content and not self.og_image:
                    self.og_image = content


def slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in value.upper())
    return "-".join(part for part in cleaned.split("-") if part)


def download(url: str, referer: str | None = None) -> bytes:
    headers = dict(UA)
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} para {url}")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise RuntimeError(f"imagen demasiado grande: {url}")
    return data


def valid_image(data: bytes, content_type: str | None = None) -> bool:
    if content_type and content_type not in {
        "image/jpeg", "image/png", "image/webp",
    }:
        return False
    if data.startswith(b"\xff\xd8\xff"):
        return True
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return True
    return False


def normalize(data: bytes) -> tuple[bytes, str]:
    img = Image.open(__import__("io").BytesIO(data))
    img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    out = __import__("io").BytesIO()
    img.save(out, format="WEBP", quality=82, method=6)
    return out.getvalue(), "image/webp"


def extract_og_image(page_url: str) -> str | None:
    try:
        req = urllib.request.Request(page_url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read(2_000_000).decode("utf-8", errors="ignore")
    except Exception:
        return None
    parser = OgImageParser()
    parser.feed(html)
    if parser.og_image:
        return urllib.parse.urljoin(page_url, parser.og_image)
    return None


def load_manifest() -> list[dict[str, Any]]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return []


def save_manifest(entries: list[dict[str, Any]]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_manifest()
    changed = False
    for entry in entries:
        brand = entry.get("brand", "")
        model = entry.get("model", "")
        file_base = entry.get("file") or slug(f"{brand}-{model}")
        out_path = IMAGES_DIR / f"{file_base}.webp"
        if out_path.exists():
            entry["file"] = file_base
            continue

        url = entry.get("image_url")
        referer = entry.get("page_url")
        if not url and entry.get("page_url"):
            url = extract_og_image(entry["page_url"])
            referer = entry["page_url"]
        if not url:
            print(f"SIN IMAGEN: {brand} {model}")
            continue

        try:
            data = download(url, referer)
            if not valid_image(data):
                print(f"NO ES IMAGEN VALIDA: {brand} {model} ({url})")
                continue
            data, content_type = normalize(data)
            out_path.write_bytes(data)
            entry["file"] = file_base
            entry["image_url"] = url
            entry["content_type"] = content_type
            entry["source"] = entry.get("source") or "official"
            changed = True
            print(f"OK: {brand} {model} -> {out_path.name} ({len(data)} bytes)")
        except Exception as exc:  # noqa: BLE001 - continuar con el siguiente modelo
            print(f"ERROR: {brand} {model}: {exc}")

    if changed:
        save_manifest(entries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
