from __future__ import annotations

from egm_common.db import create_engine, create_session_factory, init_models
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    schema=settings.db_schema,
    supabase_ref=settings.supabase_ref,
    supabase_password=settings.supabase_db_password,
)
SessionLocal = create_session_factory(engine)


async def get_session():
    async with SessionLocal() as session:
        yield session
