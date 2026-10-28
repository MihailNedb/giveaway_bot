"""Бизнес-логика управления администраторами."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Admin
from app.db.repository import AdminRepository


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.admins = AdminRepository(session)

    async def is_admin(self, user_id: int) -> bool:
        return await self.admins.is_admin(user_id)

    async def add_admin(self, user_id: int, username: str | None = None) -> Admin:
        admin = await self.admins.add(user_id, username)
        await self.session.commit()
        return admin

    async def remove_admin(self, user_id: int) -> bool:
        removed = await self.admins.remove(user_id)
        await self.session.commit()
        return removed

    async def list_admins(self) -> list[Admin]:
        return await self.admins.list_all()

    async def ensure_initial_admins(self, user_ids: list[int]) -> None:
        for user_id in user_ids:
            await self.admins.add(user_id)
        await self.session.commit()
