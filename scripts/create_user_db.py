from __future__ import annotations

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "libs"))

from app.db import engine
from egm_common.auth import hash_password
from sqlalchemy import text

USERNAME = os.getenv("AUTH_USERNAME", "Playcell")
PASSWORD = os.getenv("AUTH_PASSWORD", "playcellalex")


async def main() -> None:
    password_hash = hash_password(PASSWORD)
    user_id = str(uuid.uuid4())
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, role, is_active) "
                "VALUES (:id, :username, :password_hash, 'admin', true) "
                "ON CONFLICT (username) DO NOTHING"
            ),
            {"id": user_id, "username": USERNAME, "password_hash": password_hash},
        )
    print(f"Usuario '{USERNAME}' listo (contraseña hasheada en BD).")
    await engine.dispose()


asyncio.run(main())
