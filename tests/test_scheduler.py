"""Тесты фоновой проверки дедлайнов (process_expired_giveaways)."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.bot.scheduler import process_expired_giveaways
from app.config import Settings
from app.db.models import GiveawayStatus
from app.db.session import create_engine_and_sessionmaker, init_db
from app.services.giveaway_service import GiveawayService

CHANNEL_ID = -1001234567890


@pytest.fixture
def settings() -> Settings:
    return Settings(bot_token="test-token", channel_id=CHANNEL_ID, channel_username="test_channel")


@pytest.mark.asyncio
async def test_expired_giveaway_with_participants_gets_winner_and_announcement(settings):
    engine, session_factory = create_engine_and_sessionmaker("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        service = GiveawayService(session)
        giveaway = await service.create_giveaway(
            CHANNEL_ID, title="Приз", deadline=datetime.utcnow() - timedelta(minutes=1)
        )
        await service.join(giveaway.id, user_id=1, username="u1", first_name="A")
        giveaway_id = giveaway.id

    bot = AsyncMock()
    await process_expired_giveaways(bot, session_factory, settings)

    bot.send_message.assert_awaited_once()
    call_kwargs = bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == CHANNEL_ID
    assert "Приз" in call_kwargs["text"]

    async with session_factory() as session:
        service = GiveawayService(session)
        updated = await service.giveaways.get_by_id(giveaway_id)
        assert updated.status == GiveawayStatus.FINISHED

    await engine.dispose()


@pytest.mark.asyncio
async def test_expired_giveaway_without_participants_gets_cancelled(settings):
    engine, session_factory = create_engine_and_sessionmaker("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        service = GiveawayService(session)
        giveaway = await service.create_giveaway(
            CHANNEL_ID, title="Приз без участников", deadline=datetime.utcnow() - timedelta(minutes=1)
        )
        giveaway_id = giveaway.id

    bot = AsyncMock()
    await process_expired_giveaways(bot, session_factory, settings)

    bot.send_message.assert_not_awaited()

    async with session_factory() as session:
        service = GiveawayService(session)
        updated = await service.giveaways.get_by_id(giveaway_id)
        assert updated.status == GiveawayStatus.CANCELLED

    await engine.dispose()


@pytest.mark.asyncio
async def test_non_expired_giveaway_is_not_touched(settings):
    engine, session_factory = create_engine_and_sessionmaker("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    async with session_factory() as session:
        service = GiveawayService(session)
        giveaway = await service.create_giveaway(
            CHANNEL_ID, title="Приз", deadline=datetime.utcnow() + timedelta(minutes=30)
        )
        giveaway_id = giveaway.id

    bot = AsyncMock()
    await process_expired_giveaways(bot, session_factory, settings)

    bot.send_message.assert_not_awaited()

    async with session_factory() as session:
        service = GiveawayService(session)
        updated = await service.giveaways.get_by_id(giveaway_id)
        assert updated.status == GiveawayStatus.ACTIVE

    await engine.dispose()
