"""Фоновая задача для автоматического завершения розыгрышей по дедлайну."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bot.texts import winners_announcement_text
from app.config import Settings
from app.services.giveaway_service import GiveawayService, NoParticipantsError

logger = logging.getLogger(__name__)


async def process_expired_giveaways(
    bot: Bot, session_factory: async_sessionmaker, settings: Settings
) -> None:
    async with session_factory() as session:
        service = GiveawayService(session)
        expired = await service.find_expired_active_giveaways()

        for giveaway in expired:
            try:
                winners = await service.pick_winners(giveaway.id)
            except NoParticipantsError:
                await service.cancel_giveaway(giveaway.id)
                logger.info("Розыгрыш %s отменён по дедлайну: нет участников", giveaway.id)
                continue

            channel = await service.channels.get_by_telegram_id(settings.channel_id)
            chat_id = channel.telegram_chat_id if channel else settings.channel_id
            text = winners_announcement_text(giveaway, winners)
            try:
                await bot.send_message(chat_id=chat_id, text=text)
            except Exception:
                logger.exception(
                    "Не удалось отправить объявление победителя для розыгрыша %s", giveaway.id
                )


async def deadline_checker_loop(
    bot: Bot, session_factory: async_sessionmaker, settings: Settings
) -> None:
    while True:
        try:
            await process_expired_giveaways(bot, session_factory, settings)
        except Exception:
            logger.exception("Ошибка при проверке дедлайнов розыгрышей")
        await asyncio.sleep(settings.deadline_check_interval)
