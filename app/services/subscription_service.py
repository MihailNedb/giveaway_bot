"""Проверка подписки пользователя на канал через Bot API."""
from __future__ import annotations

from aiogram import Bot

_ALLOWED_STATUSES = {"member", "administrator", "creator"}


class SubscriptionService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def is_subscribed(self, channel_id: int, user_id: int) -> bool:
        try:
            member = await self.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        except Exception:
            return False
        return member.status in _ALLOWED_STATUSES
