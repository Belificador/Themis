"""Async SQLAlchemy helpers shared by the services."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)


def _supabase_schema_url(
    database_url: str, ref: str, password: str, schema: str
) -> str:
    """Construye una URL de Supabase con SSL y search_path por esquema."""
    host = f"db.{ref}.supabase.co"
    return f"postgresql+asyncpg://postgres:{password}@{host}:5432/postgres"


def create_engine(
    database_url: str,
    schema: Optional[str] = None,
    supabase_ref: Optional[str] = None,
    supabase_password: Optional[str] = None,
) -> AsyncEngine:
    if supabase_ref and supabase_password and schema:
        database_url = _supabase_schema_url(
            database_url, supabase_ref, supabase_password, schema
        )

    engine = create_async_engine(database_url, pool_pre_ping=True, future=True)

    if schema:

        @event.listens_for(engine.sync_engine, "connect")
        def _set_search_path(dbapi_connection, connection_record):
            with dbapi_connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{schema}"')

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_models(
    engine: AsyncEngine,
    base,
    schema: Optional[str] = None,
    attempts: int = 30,
    delay_seconds: float = 2.0,
) -> None:
    """Create tables, retrying while the database becomes ready."""
    for attempt in range(1, attempts + 1):
        try:
            async with engine.begin() as connection:
                if schema:
                    await connection.execute(
                        f'CREATE SCHEMA IF NOT EXISTS "{schema}"'
                    )
                await connection.run_sync(base.metadata.create_all)
            logger.info("database schema ready")
            return
        except Exception as exc:  # noqa: BLE001 - startup race with postgres
            logger.warning(
                "database not ready (attempt %s/%s): %s", attempt, attempts, exc
            )
            if attempt == attempts:
                raise
            await asyncio.sleep(delay_seconds)
