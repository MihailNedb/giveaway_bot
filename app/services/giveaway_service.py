"""Бизнес-логика работы с розыгрышами."""
from __future__ import annotations

import csv
import io
import random
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Giveaway, GiveawayStatus, Participant, Winner
from app.db.repository import (
    ChannelRepository,
    GiveawayRepository,
    ParticipantRepository,
    WinnerRepository,
)


class GiveawayError(Exception):
    pass


class ActiveGiveawayExistsError(GiveawayError):
    pass


class GiveawayNotFoundError(GiveawayError):
    pass


class GiveawayNotActiveError(GiveawayError):
    pass


class NoParticipantsError(GiveawayError):
    pass


class GiveawayService:
    def __init__(self, session: AsyncSession, rng: random.Random | None = None):
        self.session = session
        self.channels = ChannelRepository(session)
        self.giveaways = GiveawayRepository(session)
        self.participants = ParticipantRepository(session)
        self.winners = WinnerRepository(session)
        self._rng = rng or random.Random()

    async def create_giveaway(
        self,
        telegram_chat_id: int,
        title: str,
        description: str | None = None,
        photo_file_id: str | None = None,
        winner_count: int = 1,
        deadline: datetime | None = None,
        channel_username: str | None = None,
        channel_title: str | None = None,
    ) -> Giveaway:
        if winner_count < 1:
            raise ValueError("winner_count должен быть не меньше 1")

        channel = await self.channels.get_or_create(
            telegram_chat_id, username=channel_username, title=channel_title
        )
        active = await self.giveaways.get_active_for_channel(channel.id)
        if active is not None:
            raise ActiveGiveawayExistsError(
                f"В канале уже есть активный розыгрыш (id={active.id})"
            )

        giveaway = await self.giveaways.create(
            channel_id=channel.id,
            title=title,
            description=description,
            photo_file_id=photo_file_id,
            winner_count=winner_count,
            deadline=deadline,
        )
        await self.session.commit()
        return giveaway

    async def register_message(self, giveaway_id: int, message_id: int) -> None:
        await self.giveaways.set_message_id(giveaway_id, message_id)
        await self.session.commit()

    async def join(
        self,
        giveaway_id: int,
        user_id: int,
        username: str | None,
        first_name: str | None,
    ) -> bool:
        giveaway = await self.giveaways.get_by_id(giveaway_id)
        if giveaway is None:
            raise GiveawayNotFoundError(f"Розыгрыш {giveaway_id} не найден")
        if giveaway.status != GiveawayStatus.ACTIVE:
            raise GiveawayNotActiveError("Розыгрыш не активен")

        _, is_new = await self.participants.add(
            giveaway_id=giveaway_id,
            user_id=user_id,
            username=username,
            first_name=first_name,
        )
        await self.session.commit()
        return is_new

    async def get_active_giveaway(self, telegram_chat_id: int) -> Giveaway | None:
        channel = await self.channels.get_by_telegram_id(telegram_chat_id)
        if channel is None:
            return None
        return await self.giveaways.get_active_for_channel(channel.id)

    async def list_participants(self, giveaway_id: int) -> list[Participant]:
        giveaway = await self.giveaways.get_by_id(giveaway_id)
        if giveaway is None:
            raise GiveawayNotFoundError(f"Розыгрыш {giveaway_id} не найден")
        return await self.participants.list_for_giveaway(giveaway_id)

    async def pick_winners(self, giveaway_id: int, custom_announcement: str | None = None) -> list[Winner]:
        giveaway = await self.giveaways.get_by_id(giveaway_id)
        if giveaway is None:
            raise GiveawayNotFoundError(f"Розыгрыш {giveaway_id} не найден")
        if giveaway.status != GiveawayStatus.ACTIVE:
            raise GiveawayNotActiveError("Розыгрыш не активен")

        participants = await self.participants.list_for_giveaway(giveaway_id)
        if not participants:
            raise NoParticipantsError("Нет участников для выбора победителя")

        count = min(giveaway.winner_count, len(participants))
        chosen = self._rng.sample(participants, k=count)
        winners = await self.winners.add_many(giveaway_id, chosen)

        await self.giveaways.finish(giveaway_id)
        await self.session.commit()
        return winners

    async def cancel_giveaway(self, giveaway_id: int) -> None:
        giveaway = await self.giveaways.get_by_id(giveaway_id)
        if giveaway is None:
            raise GiveawayNotFoundError(f"Розыгрыш {giveaway_id} не найден")
        await self.giveaways.cancel(giveaway_id)
        await self.session.commit()

    async def delete_giveaway(self, giveaway_id: int) -> bool:
        deleted = await self.giveaways.delete(giveaway_id)
        await self.session.commit()
        return deleted

    async def find_expired_active_giveaways(self, now: datetime | None = None) -> list[Giveaway]:
        now = now or datetime.utcnow()
        return await self.giveaways.get_active_with_expired_deadline(now)

    async def export_participants_csv(self, giveaway_id: int) -> str:
        giveaway = await self.giveaways.get_by_id(giveaway_id)
        if giveaway is None:
            raise GiveawayNotFoundError(f"Розыгрыш {giveaway_id} не найден")
        participants = await self.participants.list_for_giveaway(giveaway_id)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["user_id", "username", "first_name", "joined_at"])
        for p in participants:
            writer.writerow(
                [
                    p.user_id,
                    f"@{p.username}" if p.username else "",
                    p.first_name or "",
                    p.joined_at.isoformat() if p.joined_at else "",
                ]
            )
        return buffer.getvalue()
