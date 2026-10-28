"""Тесты слоя репозиториев (прямой доступ к БД)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.db.models import GiveawayStatus
from app.db.repository import (
    AdminRepository,
    ChannelRepository,
    GiveawayRepository,
    ParticipantRepository,
    WinnerRepository,
)


@pytest.mark.asyncio
async def test_channel_get_or_create_creates_once(session):
    repo = ChannelRepository(session)
    channel1 = await repo.get_or_create(-1001, username="chan", title="Chan")
    channel2 = await repo.get_or_create(-1001, username="other", title="Other")

    assert channel1.id == channel2.id
    assert channel2.username == "chan"


@pytest.mark.asyncio
async def test_giveaway_create_and_get_active(session):
    channels = ChannelRepository(session)
    giveaways = GiveawayRepository(session)

    channel = await channels.get_or_create(-1001)
    giveaway = await giveaways.create(channel_id=channel.id, title="Приз")

    active = await giveaways.get_active_for_channel(channel.id)
    assert active is not None
    assert active.id == giveaway.id
    assert active.status == GiveawayStatus.ACTIVE


@pytest.mark.asyncio
async def test_giveaway_finish_sets_status_and_timestamp(session):
    channels = ChannelRepository(session)
    giveaways = GiveawayRepository(session)
    channel = await channels.get_or_create(-1001)
    giveaway = await giveaways.create(channel_id=channel.id, title="Приз")

    await giveaways.finish(giveaway.id)

    updated = await giveaways.get_by_id(giveaway.id)
    assert updated.status == GiveawayStatus.FINISHED
    assert updated.finished_at is not None


@pytest.mark.asyncio
async def test_giveaway_delete_removes_record_and_participants(session):
    channels = ChannelRepository(session)
    giveaways = GiveawayRepository(session)
    participants = ParticipantRepository(session)

    channel = await channels.get_or_create(-1001)
    giveaway = await giveaways.create(channel_id=channel.id, title="Приз")
    await participants.add(giveaway.id, user_id=1, username="u1", first_name="A")

    deleted = await giveaways.delete(giveaway.id)
    assert deleted is True
    assert await giveaways.get_by_id(giveaway.id) is None

    missing = await giveaways.delete(9999)
    assert missing is False


@pytest.mark.asyncio
async def test_giveaway_get_active_with_expired_deadline(session):
    channels = ChannelRepository(session)
    giveaways = GiveawayRepository(session)
    channel = await channels.get_or_create(-1001)

    past_deadline = datetime.utcnow() - timedelta(minutes=5)
    future_deadline = datetime.utcnow() + timedelta(minutes=5)

    expired = await giveaways.create(channel_id=channel.id, title="Истёкший", deadline=past_deadline)
    await giveaways.create(channel_id=channel.id, title="Будущий", deadline=future_deadline)

    result = await giveaways.get_active_with_expired_deadline(datetime.utcnow())
    assert len(result) == 1
    assert result[0].id == expired.id


@pytest.mark.asyncio
async def test_participant_add_prevents_duplicates(session):
    channels = ChannelRepository(session)
    giveaways = GiveawayRepository(session)
    participants = ParticipantRepository(session)

    channel = await channels.get_or_create(-1001)
    giveaway = await giveaways.create(channel_id=channel.id, title="Приз")

    _, is_new1 = await participants.add(giveaway.id, user_id=1, username="u1", first_name="A")
    _, is_new2 = await participants.add(giveaway.id, user_id=1, username="u1", first_name="A")

    assert is_new1 is True
    assert is_new2 is False
    assert await participants.count_for_giveaway(giveaway.id) == 1


@pytest.mark.asyncio
async def test_winner_repository_add_many(session):
    channels = ChannelRepository(session)
    giveaways = GiveawayRepository(session)
    participants = ParticipantRepository(session)
    winners = WinnerRepository(session)

    channel = await channels.get_or_create(-1001)
    giveaway = await giveaways.create(channel_id=channel.id, title="Приз")
    p1, _ = await participants.add(giveaway.id, user_id=1, username="u1", first_name="A")
    p2, _ = await participants.add(giveaway.id, user_id=2, username="u2", first_name="B")

    created = await winners.add_many(giveaway.id, [p1, p2])
    assert len(created) == 2

    listed = await winners.list_for_giveaway(giveaway.id)
    assert {w.user_id for w in listed} == {1, 2}


@pytest.mark.asyncio
async def test_admin_repository_add_remove_is_admin(session):
    repo = AdminRepository(session)

    assert await repo.is_admin(42) is False

    await repo.add(42, username="owner")
    assert await repo.is_admin(42) is True

    await repo.add(42, username="owner")
    admins = await repo.list_all()
    assert len(admins) == 1

    removed = await repo.remove(42)
    assert removed is True
    assert await repo.is_admin(42) is False

    assert await repo.remove(999) is False
