#!/usr/bin/env python3
"""Crea el usuario único Playcell (contraseña hasheada en el backend).

Usage:
    BASE_URL=https://console-themis-b6t5p.sprites.app python3 scripts/create_user.py
    # o local:
    BASE_URL=http://127.0.0.1:8000 python3 scripts/create_user.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
USERNAME = os.getenv("AUTH_USERNAME", "Playcell")
PASSWORD = os.getenv("AUTH_PASSWORD", "playcellalex")


def http(method: str, path: str, payload: dict | None = None, timeout: float = 30.0):
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


def main() -> int:
    # Genera hash de bcrypt localmente para no enviar la contraseña en texto plano al servidor
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    password_hash = pwd_context.hash(PASSWORD)

    print(f"Creando usuario '{USERNAME}' en {BASE_URL}...")

    status, body = http(
        "POST",
        "/api/auth/users",
        {
            "username": USERNAME,
            "password_hash": password_hash,
            "role": "admin",
            "is_active": True,
        },
    )

    if status in (200, 201):
        print(f"Usuario creado: {body}")
        return 0
    if status == 409:
        print("El usuario ya existe.")
        return 0
    print(f"Error al crear usuario: {status} {body}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
