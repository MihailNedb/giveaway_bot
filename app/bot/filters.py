"""Кастомные фильтры aiogram."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_service import AdminService


class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        admin_service = AdminService(session)
        return await admin_service.is_admin(message.from_user.id)
