"""Тесты SubscriptionService с мок-объектом Bot."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.subscription_service import SubscriptionService


@pytest.mark.parametrize("status", ["member", "administrator", "creator"])
@pytest.mark.asyncio
async def test_is_subscribed_true_for_allowed_statuses(status):
    bot = AsyncMock()
    bot.get_chat_member.return_value = SimpleNamespace(status=status)
    service = SubscriptionService(bot)

    assert await service.is_subscribed(channel_id=-100, user_id=1) is True


@pytest.mark.parametrize("status", ["left", "kicked", "restricted"])
@pytest.mark.asyncio
async def test_is_subscribed_false_for_disallowed_statuses(status):
    bot = AsyncMock()
    bot.get_chat_member.return_value = SimpleNamespace(status=status)
    service = SubscriptionService(bot)

    assert await service.is_subscribed(channel_id=-100, user_id=1) is False


@pytest.mark.asyncio
async def test_is_subscribed_false_when_api_raises():
    bot = AsyncMock()
    bot.get_chat_member.side_effect = Exception("Bad Request: user not found")
    service = SubscriptionService(bot)

    assert await service.is_subscribed(channel_id=-100, user_id=1) is False
