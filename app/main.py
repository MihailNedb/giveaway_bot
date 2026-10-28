"""Точка входа бота."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.commands import setup_bot_commands
from app.bot.handlers import giveaway_admin, giveaway_public
from app.bot.middlewares import DbSessionMiddleware
from app.bot.scheduler import deadline_checker_loop
from app.config import load_settings
from app.db.session import create_engine_and_sessionmaker, init_db
from app.services.admin_service import AdminService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    engine, session_factory = create_engine_and_sessionmaker(settings.database_url)
    await init_db(engine)

    async with session_factory() as session:
        admin_service = AdminService(session)
        await admin_service.ensure_initial_admins(settings.initial_admin_ids)

    dp.update.middleware(DbSessionMiddleware(session_factory))
    dp["settings"] = settings

    dp.include_router(giveaway_admin.router)
    dp.include_router(giveaway_public.router)

    await setup_bot_commands(bot, settings.initial_admin_ids)

    scheduler_task = asyncio.create_task(
        deadline_checker_loop(bot, session_factory, settings)
    )

    try:
        logger.info("Бот запущен и готов к работе...")
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
