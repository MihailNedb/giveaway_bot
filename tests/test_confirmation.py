"""Тесты механизма хранения подтверждаемых действий (FSM)."""
from __future__ import annotations

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

from app.bot.confirmation import (
    ConfirmationStates,
    clear_pending_action,
    get_pending_action,
    request_confirmation,
)


def _make_state() -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=100, user_id=100)
    return FSMContext(storage=storage, key=key)


@pytest.mark.asyncio
async def test_request_confirmation_stores_action_and_payload():
    state = _make_state()
    await request_confirmation(state, action="delete_giveaway", payload={"giveaway_id": 5})

    current_state = await state.get_state()
    assert current_state == ConfirmationStates.waiting_confirmation.state

    pending = await get_pending_action(state)
    assert pending is not None
    action, payload = pending
    assert action == "delete_giveaway"
    assert payload == {"giveaway_id": 5}


@pytest.mark.asyncio
async def test_get_pending_action_returns_none_when_nothing_stored():
    state = _make_state()
    pending = await get_pending_action(state)
    assert pending is None


@pytest.mark.asyncio
async def test_clear_pending_action_resets_state():
    state = _make_state()
    await request_confirmation(state, action="cancel_giveaway", payload={"giveaway_id": 1})

    await clear_pending_action(state)

    assert await get_pending_action(state) is None
    assert await state.get_state() is None
