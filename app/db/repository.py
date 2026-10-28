"""Репозитории — слой доступа к данным (CRUD) без бизнес-логики."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Admin, Channel, Giveaway, GiveawayStatus, Participant, Winner


class ChannelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_chat_id: int) -> Channel | None:
        result = await self.session.execute(
            select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self, telegram_chat_id: int, username: str | None = None, title: str | None = None
    ) -> Channel:
        channel = await self.get_by_telegram_id(telegram_chat_id)
        if channel:
            return channel
        channel = Channel(
            telegram_chat_id=telegram_chat_id, username=username, title=title
        )
        self.session.add(channel)
        await self.session.flush()
        return channel


class GiveawayRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        channel_id: int,
        title: str,
        description: str | None = None,
        photo_file_id: str | None = None,
        winner_count: int = 1,
        deadline: datetime | None = None,
    ) -> Giveaway:
        giveaway = Giveaway(
            channel_id=channel_id,
            title=title,
            description=description,
            photo_file_id=photo_file_id,
            winner_count=winner_count,
            deadline=deadline,
            status=GiveawayStatus.ACTIVE,
        )
        self.session.add(giveaway)
        await self.session.flush()
        return giveaway

    async def get_by_id(self, giveaway_id: int) -> Giveaway | None:
        result = await self.session.execute(
            select(Giveaway).where(Giveaway.id == giveaway_id)
        )
        return result.scalar_one_or_none()

    async def get_active_for_channel(self, channel_id: int) -> Giveaway | None:
        result = await self.session.execute(
            select(Giveaway).where(
                Giveaway.channel_id == channel_id,
                Giveaway.status == GiveawayStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_with_expired_deadline(self, now: datetime) -> list[Giveaway]:
        result = await self.session.execute(
            select(Giveaway).where(
                Giveaway.status == GiveawayStatus.ACTIVE,
                Giveaway.deadline.is_not(None),
                Giveaway.deadline <= now,
            )
        )
        return list(result.scalars().all())

    async def set_message_id(self, giveaway_id: int, message_id: int) -> None:
        giveaway = await self.get_by_id(giveaway_id)
        if giveaway:
            giveaway.message_id = message_id
            await self.session.flush()

    async def finish(self, giveaway_id: int) -> None:
        giveaway = await self.get_by_id(giveaway_id)
        if giveaway:
            giveaway.status = GiveawayStatus.FINISHED
            giveaway.finished_at = datetime.utcnow()
            await self.session.flush()

    async def cancel(self, giveaway_id: int) -> None:
        giveaway = await self.get_by_id(giveaway_id)
        if giveaway:
            giveaway.status = GiveawayStatus.CANCELLED
            giveaway.finished_at = datetime.utcnow()
            await self.session.flush()

    async def delete(self, giveaway_id: int) -> bool:
        giveaway = await self.get_by_id(giveaway_id)
        if not giveaway:
            return False
        await self.session.delete(giveaway)
        await self.session.flush()
        return True


class ParticipantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        giveaway_id: int,
        user_id: int,
        username: str | None,
        first_name: str | None,
    ) -> tuple[Participant, bool]:
        existing = await self.get(giveaway_id, user_id)
        if existing:
            return existing, False
        participant = Participant(
            giveaway_id=giveaway_id,
            user_id=user_id,
            username=username,
            first_name=first_name,
        )
        self.session.add(participant)
        await self.session.flush()
        return participant, True

    async def get(self, giveaway_id: int, user_id: int) -> Participant | None:
        result = await self.session.execute(
            select(Participant).where(
                Participant.giveaway_id == giveaway_id,
                Participant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_giveaway(self, giveaway_id: int) -> list[Participant]:
        result = await self.session.execute(
            select(Participant).where(Participant.giveaway_id == giveaway_id)
        )
        return list(result.scalars().all())

    async def count_for_giveaway(self, giveaway_id: int) -> int:
        participants = await self.list_for_giveaway(giveaway_id)
        return len(participants)


class WinnerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_many(self, giveaway_id: int, participants: list[Participant]) -> list[Winner]:
        winners = []
        for p in participants:
            winner = Winner(
                giveaway_id=giveaway_id,
                user_id=p.user_id,
                username=p.username,
                first_name=p.first_name,
            )
            self.session.add(winner)
            winners.append(winner)
        await self.session.flush()
        return winners

    async def list_for_giveaway(self, giveaway_id: int) -> list[Winner]:
        result = await self.session.execute(
            select(Winner).where(Winner.giveaway_id == giveaway_id)
        )
        return list(result.scalars().all())


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_admin(self, user_id: int) -> bool:
        result = await self.session.execute(select(Admin).where(Admin.user_id == user_id))
        return result.scalar_one_or_none() is not None

    async def add(self, user_id: int, username: str | None = None) -> Admin:
        existing = await self.session.execute(select(Admin).where(Admin.user_id == user_id))
        admin = existing.scalar_one_or_none()
        if admin:
            return admin
        admin = Admin(user_id=user_id, username=username)
        self.session.add(admin)
        await self.session.flush()
        return admin

    async def remove(self, user_id: int) -> bool:
        result = await self.session.execute(select(Admin).where(Admin.user_id == user_id))
        admin = result.scalar_one_or_none()
        if not admin:
            return False
        await self.session.delete(admin)
        await self.session.flush()
        return True

    async def list_all(self) -> list[Admin]:
        result = await self.session.execute(select(Admin))
        return list(result.scalars().all())
