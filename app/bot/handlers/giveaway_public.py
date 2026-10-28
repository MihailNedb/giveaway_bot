"""Публичные хендлеры: участие в розыгрыше по нажатию кнопки."""
from __future__ import annotations

from aiogram import Bot, F, Router, types
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import JOIN_CALLBACK_PREFIX
from app.config import Settings
from app.services.giveaway_service import (
    GiveawayError,
    GiveawayNotActiveError,
    GiveawayNotFoundError,
    GiveawayService,
)
from app.services.subscription_service import SubscriptionService

router = Router(name="giveaway_public")


@router.callback_query(F.data.startswith(JOIN_CALLBACK_PREFIX))
async def handle_join(
    callback: types.CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
):
    giveaway_id_raw = callback.data.removeprefix(JOIN_CALLBACK_PREFIX)
    if not giveaway_id_raw.isdigit():
        await callback.answer("Некорректный розыгрыш.", show_alert=True)
        return
    giveaway_id = int(giveaway_id_raw)

    subscription_service = SubscriptionService(bot)
    is_subscribed = await subscription_service.is_subscribed(
        settings.channel_id, callback.from_user.id
    )
    if not is_subscribed:
        await callback.answer("Чтобы участвовать, подпишитесь на канал!", show_alert=True)
        return

    service = GiveawayService(session)
    try:
        is_new = await service.join(
            giveaway_id=giveaway_id,
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )
    except GiveawayNotFoundError:
        await callback.answer("Розыгрыш не найден.", show_alert=True)
        return
    except GiveawayNotActiveError:
        await callback.answer("Этот розыгрыш уже завершён.", show_alert=True)
        return
    except GiveawayError as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)
        return

    if is_new:
        await callback.answer("🎉 Вы успешно зарегистрированы!", show_alert=True)
    else:
        await callback.answer("Вы уже принимаете участие!", show_alert=False)
