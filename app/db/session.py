"""Фабрика сессий и инициализация базы данных."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import Base


def create_engine_and_sessionmaker(database_url: str):
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    return engine, session_factory


async def init_db(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Совместимость с уже существующей SQLite-базой предыдущей версии.
        if engine.url.get_backend_name() == "sqlite":
            result = await conn.exec_driver_sql("PRAGMA table_info(giveaways)")
            columns = {row[1] for row in result.fetchall()}
            if "description" not in columns:
                await conn.exec_driver_sql("ALTER TABLE giveaways ADD COLUMN description TEXT")
            if "photo_file_id" not in columns:
                await conn.exec_driver_sql("ALTER TABLE giveaways ADD COLUMN photo_file_id VARCHAR(255)")
