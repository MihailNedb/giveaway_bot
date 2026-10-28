"""Тесты AdminService."""
from __future__ import annotations

import pytest

from app.services.admin_service import AdminService


@pytest.mark.asyncio
async def test_add_and_check_admin(session):
    service = AdminService(session)

    assert await service.is_admin(1) is False
    await service.add_admin(1, username="owner")
    assert await service.is_admin(1) is True


@pytest.mark.asyncio
async def test_remove_admin(session):
    service = AdminService(session)
    await service.add_admin(1)

    removed = await service.remove_admin(1)
    assert removed is True
    assert await service.is_admin(1) is False

    assert await service.remove_admin(1) is False


@pytest.mark.asyncio
async def test_ensure_initial_admins_is_idempotent(session):
    service = AdminService(session)
    await service.ensure_initial_admins([1, 2, 3])
    await service.ensure_initial_admins([1, 2, 3])

    admins = await service.list_admins()
    assert {a.user_id for a in admins} == {1, 2, 3}
    assert len(admins) == 3
