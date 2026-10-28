"""Тесты текстовых шаблонов — проверка требования об эмодзи."""
from __future__ import annotations

from datetime import datetime

from app.bot.texts import (
    giveaway_post_text,
    preview_delete_giveaway,
    preview_new_giveaway,
    winners_announcement_text,
)
from app.db.models import Giveaway, GiveawayStatus, Winner


def _make_giveaway(**kwargs) -> Giveaway:
    defaults = dict(
        id=1,
        channel_id=1,
        title="Тестовый приз",
        status=GiveawayStatus.ACTIVE,
        winner_count=1,
        deadline=None,
    )
    defaults.update(kwargs)
    return Giveaway(**defaults)


def test_giveaway_post_text_has_no_party_emoji():
    giveaway = _make_giveaway()
    text = giveaway_post_text(giveaway)
    assert "🎉" not in text
    assert "Тестовый приз" in text


def test_giveaway_post_text_includes_deadline_when_set():
    giveaway = _make_giveaway(deadline=datetime(2026, 1, 1, 12, 0))
    text = giveaway_post_text(giveaway)
    assert "⏰" in text
    assert "01.01.2026" in text


def test_giveaway_post_text_without_deadline_has_no_clock_emoji():
    giveaway = _make_giveaway(deadline=None)
    text = giveaway_post_text(giveaway)
    assert "⏰" not in text


def test_winners_announcement_keeps_trophy_emoji():
    giveaway = _make_giveaway(status=GiveawayStatus.FINISHED)
    winner = Winner(id=1, giveaway_id=1, user_id=42, username="winner", first_name="W")
    text = winners_announcement_text(giveaway, [winner])
    assert "🏆" in text
    assert "@winner" in text


def test_preview_new_giveaway_has_no_party_emoji_and_mentions_channel():
    text = preview_new_giveaway("Приз", 60, "mychannel")
    assert "🎉" not in text
    assert "@mychannel" in text
    assert "Приз" in text


def test_preview_delete_giveaway_mentions_irreversibility():
    giveaway = _make_giveaway()
    text = preview_delete_giveaway(giveaway, participants_count=5)
    assert "необратимо" in text
    assert "5" in text
