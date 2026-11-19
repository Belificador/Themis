"""Async SQLAlchemy helpers shared by the services."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_models(
    engine: AsyncEngine,
    base,
    attempts: int = 30,
    delay_seconds: float = 2.0,
) -> None:
    """Create tables, retrying while the database container becomes ready."""
    for attempt in range(1, attempts + 1):
        try:
            async with engine.begin() as connection:
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
