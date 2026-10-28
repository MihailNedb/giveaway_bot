"""Тесты бизнес-логики GiveawayService."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

import pytest

from app.db.models import GiveawayStatus
from app.services.giveaway_service import (
    ActiveGiveawayExistsError,
    GiveawayNotActiveError,
    GiveawayNotFoundError,
    GiveawayService,
    NoParticipantsError,
)

CHANNEL_ID = -1001234567890


@pytest.mark.asyncio
async def test_create_giveaway_success(session):
    service = GiveawayService(session)
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз 1")

    assert giveaway.id is not None
    assert giveaway.status == GiveawayStatus.ACTIVE
    assert giveaway.winner_count == 1


@pytest.mark.asyncio
async def test_create_giveaway_fails_if_active_exists(session):
    service = GiveawayService(session)
    await service.create_giveaway(CHANNEL_ID, title="Приз 1")

    with pytest.raises(ActiveGiveawayExistsError):
        await service.create_giveaway(CHANNEL_ID, title="Приз 2")


@pytest.mark.asyncio
async def test_create_giveaway_allows_new_after_finish(session):
    service = GiveawayService(session)
    first = await service.create_giveaway(CHANNEL_ID, title="Приз 1")
    await service.join(first.id, user_id=1, username="u1", first_name="A")
    await service.pick_winners(first.id)

    second = await service.create_giveaway(CHANNEL_ID, title="Приз 2")
    assert second.id != first.id
    assert second.status == GiveawayStatus.ACTIVE


@pytest.mark.asyncio
async def test_create_giveaway_rejects_invalid_winner_count(session):
    service = GiveawayService(session)
    with pytest.raises(ValueError):
        await service.create_giveaway(CHANNEL_ID, title="Приз", winner_count=0)


@pytest.mark.asyncio
async def test_join_registers_new_participant(session):
    service = GiveawayService(session)
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз")

    is_new = await service.join(giveaway.id, user_id=1, username="u1", first_name="Ann")
    assert is_new is True

    participants = await service.list_participants(giveaway.id)
    assert len(participants) == 1
    assert participants[0].user_id == 1


@pytest.mark.asyncio
async def test_join_prevents_duplicate_registration(session):
    service = GiveawayService(session)
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз")

    first = await service.join(giveaway.id, user_id=1, username="u1", first_name="Ann")
    second = await service.join(giveaway.id, user_id=1, username="u1", first_name="Ann")

    assert first is True
    assert second is False
    participants = await service.list_participants(giveaway.id)
    assert len(participants) == 1


@pytest.mark.asyncio
async def test_join_fails_for_unknown_giveaway(session):
    service = GiveawayService(session)
    with pytest.raises(GiveawayNotFoundError):
        await service.join(9999, user_id=1, username=None, first_name=None)


@pytest.mark.asyncio
async def test_join_fails_for_finished_giveaway(session):
    service = GiveawayService(session)
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз")
    await service.join(giveaway.id, user_id=1, username="u1", first_name="A")
    await service.pick_winners(giveaway.id)

    with pytest.raises(GiveawayNotActiveError):
        await service.join(giveaway.id, user_id=2, username="u2", first_name="B")


@pytest.mark.asyncio
async def test_pick_winners_selects_requested_count(session):
    service = GiveawayService(session, rng=random.Random(42))
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз", winner_count=2)

    for i in range(5):
        await service.join(giveaway.id, user_id=i, username=f"u{i}", first_name=f"F{i}")

    winners = await service.pick_winners(giveaway.id)
    assert len(winners) == 2
    participant_ids = {i for i in range(5)}
    assert all(w.user_id in participant_ids for w in winners)

    finished = await service.giveaways.get_by_id(giveaway.id)
    assert finished.status == GiveawayStatus.FINISHED
    assert finished.finished_at is not None


@pytest.mark.asyncio
async def test_pick_winners_caps_at_participant_count(session):
    service = GiveawayService(session, rng=random.Random(1))
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз", winner_count=5)
    await service.join(giveaway.id, user_id=1, username="u1", first_name="A")

    winners = await service.pick_winners(giveaway.id)
    assert len(winners) == 1


@pytest.mark.asyncio
async def test_pick_winners_fails_without_participants(session):
    service = GiveawayService(session)
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз")

    with pytest.raises(NoParticipantsError):
        await service.pick_winners(giveaway.id)


@pytest.mark.asyncio
async def test_pick_winners_fails_for_already_finished_giveaway(session):
    service = GiveawayService(session)
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз")
    await service.join(giveaway.id, user_id=1, username="u1", first_name="A")
    await service.pick_winners(giveaway.id)

    with pytest.raises(GiveawayNotActiveError):
        await service.pick_winners(giveaway.id)


@pytest.mark.asyncio
async def test_cancel_giveaway_sets_status_cancelled(session):
    service = GiveawayService(session)
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз")

    await service.cancel_giveaway(giveaway.id)

    updated = await service.giveaways.get_by_id(giveaway.id)
    assert updated.status == GiveawayStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_giveaway_fails_for_unknown_id(session):
    service = GiveawayService(session)
    with pytest.raises(GiveawayNotFoundError):
        await service.cancel_giveaway(9999)


@pytest.mark.asyncio
async def test_delete_giveaway_removes_record(session):
    service = GiveawayService(session)
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз")

    deleted = await service.delete_giveaway(giveaway.id)
    assert deleted is True
    assert await service.giveaways.get_by_id(giveaway.id) is None


@pytest.mark.asyncio
async def test_delete_giveaway_returns_false_for_unknown_id(session):
    service = GiveawayService(session)
    assert await service.delete_giveaway(9999) is False


@pytest.mark.asyncio
async def test_find_expired_active_giveaways(session):
    service = GiveawayService(session)
    past_deadline = datetime.utcnow() - timedelta(minutes=1)

    expired = await service.create_giveaway(CHANNEL_ID, title="Истёкший", deadline=past_deadline)

    found = await service.find_expired_active_giveaways()
    assert len(found) == 1
    assert found[0].id == expired.id


@pytest.mark.asyncio
async def test_export_participants_csv_contains_header_and_rows(session):
    service = GiveawayService(session)
    giveaway = await service.create_giveaway(CHANNEL_ID, title="Приз")
    await service.join(giveaway.id, user_id=1, username="ivan", first_name="Иван")
    await service.join(giveaway.id, user_id=2, username=None, first_name="Елена")

    csv_text = await service.export_participants_csv(giveaway.id)
    lines = csv_text.strip().splitlines()

    assert lines[0] == "user_id,username,first_name,joined_at"
    assert len(lines) == 3
    assert "@ivan" in csv_text
    assert "Иван" in csv_text
    assert "Елена" in csv_text


@pytest.mark.asyncio
async def test_export_participants_csv_fails_for_unknown_giveaway(session):
    service = GiveawayService(session)
    with pytest.raises(GiveawayNotFoundError):
        await service.export_participants_csv(9999)


@pytest.mark.asyncio
async def test_get_active_giveaway_returns_none_for_unknown_channel(session):
    service = GiveawayService(session)
    result = await service.get_active_giveaway(CHANNEL_ID)
    assert result is None
