"""Клавиатуры для бота."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

JOIN_CALLBACK_PREFIX = "join_giveaway:"


def giveaway_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Участвовать",
                    callback_data=f"{JOIN_CALLBACK_PREFIX}{giveaway_id}",
                )
            ]
        ]
    )
