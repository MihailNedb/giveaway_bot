"""Общие фикстуры для тестов."""
from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import create_engine_and_sessionmaker, init_db


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine, session_factory = create_engine_and_sessionmaker("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    async with session_factory() as s:
        yield s
    await engine.dispose()
