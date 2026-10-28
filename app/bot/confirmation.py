"""Механизм подтверждения действий администратора перед их выполнением.

Используется FSM-хранилище aiogram для временного хранения параметров
команды между запросом подтверждения и нажатием кнопки."""
from __future__ import annotations

from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CONFIRM_CALLBACK = "confirm_action"
CANCEL_CALLBACK = "cancel_action"
SKIP_CALLBACK = "skip_step"


class ConfirmationStates(StatesGroup):
    waiting_confirmation = State()


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=CONFIRM_CALLBACK),
                InlineKeyboardButton(text="❌ Отмена", callback_data=CANCEL_CALLBACK),
            ]
        ]
    )


async def request_confirmation(
    state: FSMContext, action: str, payload: dict[str, Any]
) -> None:
    """Сохраняет действие и его параметры в FSM до подтверждения админом."""
    await state.set_state(ConfirmationStates.waiting_confirmation)
    await state.update_data(action=action, payload=payload)


async def get_pending_action(state: FSMContext) -> tuple[str, dict[str, Any]] | None:
    data = await state.get_data()
    action = data.get("action")
    if action is None:
        return None
    return action, data.get("payload", {})


async def clear_pending_action(state: FSMContext) -> None:
    await state.clear()


def skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=SKIP_CALLBACK)]
    ])
