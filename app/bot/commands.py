"""Регистрация команд бота (автодополнение по /) только для администраторов."""
from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

ADMIN_COMMANDS = [
    BotCommand(command="newgiveaway", description="Создать и опубликовать розыгрыш"),
    BotCommand(command="participants", description="Список участников розыгрыша"),
    BotCommand(command="pickwinner", description="Выбрать победителя"),
    BotCommand(command="cancelgiveaway", description="Отменить розыгрыш"),
    BotCommand(command="deletegiveaway", description="Удалить розыгрыш из базы"),
    BotCommand(command="exportparticipants", description="Экспорт участников в CSV"),
]


async def setup_bot_commands(bot: Bot, admin_ids: list[int]) -> None:
    """Устанавливает пустой список команд по умолчанию (для всех пользователей)
    и полный список — только в приватном чате с каждым админом из .env."""
    await bot.set_my_commands(commands=[], scope=BotCommandScopeDefault())

    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(
                commands=ADMIN_COMMANDS,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception:
            # Админ может ещё не писать боту (чат не инициализирован) — Telegram
            # в этом случае вернёт ошибку. Пропускаем, не прерывая запуск.
            pass
