#!/usr/bin/env python3
"""Crea el usuario Playcell directamente en la base de datos (contraseña hasheada).

Se ejecuta una sola vez. La contraseña nunca viaja en texto plano por la red.

Usage:
    SUPABASE_DB_PASSWORD=TX0dAwjHUxJVARyL DB_SCHEMA=themis \
    PYTHONPATH=/home/sprite/Themis/libs:/home/sprite/Themis/services/app \
    python3 scripts/create_user_db.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "libs"))

from app.db import engine
from egm_common.auth import hash_password
from sqlalchemy import text

USERNAME = os.getenv("AUTH_USERNAME", "Playcell")
PASSWORD = os.getenv("AUTH_PASSWORD", "playcellalex")


async def main() -> None:
    password_hash = hash_password(PASSWORD)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (username, password_hash, role, is_active) "
                "VALUES (:username, :password_hash, 'admin', true) "
                "ON CONFLICT (username) DO NOTHING"
            ),
            {"username": USERNAME, "password_hash": password_hash},
        )
    print(f"Usuario '{USERNAME}' listo (contraseña hasheada en BD).")
    await engine.dispose()


asyncio.run(main())
