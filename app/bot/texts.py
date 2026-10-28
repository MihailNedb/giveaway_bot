"""Текстовые шаблоны сообщений."""
from __future__ import annotations

from app.db.models import Giveaway, Participant, Winner


def giveaway_post_text(giveaway: Giveaway) -> str:
    parts = [giveaway.title]
    if getattr(giveaway, "description", None):
        parts.append(giveaway.description)
    parts.append("Нажмите кнопку ниже, чтобы принять участие!")
    if giveaway.deadline:
        parts.append(f"⏰ Окончание: {giveaway.deadline.strftime('%d.%m.%Y %H:%M UTC')}")
    return "\n\n".join(parts)


def winners_announcement_text(giveaway: Giveaway, winners: list[Winner], custom_announcement: str | None = None) -> str:
    header = custom_announcement or f"🏆 Розыгрыш «{giveaway.title}» завершён!"
    label = "Победитель:" if len(winners) == 1 else "Победители:"
    lines = [header, "", label]
    for w in winners:
        name = f"@{w.username}" if w.username else (w.first_name or str(w.user_id))
        lines.append(f"• {name}")
    return "\n".join(lines)


def participants_list_text(giveaway_title: str, participants: list[Participant]) -> str:
    if not participants:
        return f"Розыгрыш «{giveaway_title}»: пока нет участников."
    lines = [f"Участники розыгрыша «{giveaway_title}» ({len(participants)}):"]
    for p in participants:
        name = f"@{p.username}" if p.username else (p.first_name or str(p.user_id))
        lines.append(f"• {name} (id: {p.user_id})")
    return "\n".join(lines)


# ---------- Превью перед подтверждением ----------


def preview_new_giveaway(
    title: str,
    deadline_minutes: int | None,
    channel_username: str,
    description: str | None = None,
    has_photo: bool = False,
    winner_count: int = 1,
) -> str:
    """Показывает администратору вид будущего поста перед публикацией.

    Последние три аргумента необязательны для совместимости со старым API.
    """
    post_parts = [f"<b>{title}</b>"]
    if description:
        post_parts.append(description)
    post_parts.append("Нажмите кнопку ниже, чтобы принять участие!")
    if deadline_minutes:
        post_parts.append(f"⏰ Окончание через {deadline_minutes} мин.")
    post_parts.append(f"Количество победителей: {winner_count}")
    photo_line = "\nФото: будет добавлено" if has_photo else "\nФото: не будет"
    return (
        f"Вы хотите создать и опубликовать новый розыгрыш в канале @{channel_username}.\n\n"
        "Пост будет выглядеть так:\n"
        "――――――――――――――\n"
        + "\n\n".join(post_parts)
        + photo_line
        + ("\nДедлайн не задан" if not deadline_minutes else "")
        + "\n――――――――――――――\n"
        "[Кнопка: ✅ Участвовать]\n\n"
        "Подтвердите публикацию."
    )


def preview_pick_winner(
    giveaway: Giveaway,
    participants_count: int,
    custom_announcement: str | None = None,
) -> str:
    announcement = custom_announcement or f"🏆 Розыгрыш «{giveaway.title}» завершён!"
    return (
        f"Вы хотите выбрать победителя розыгрыша «{giveaway.title}» (id={giveaway.id}).\n"
        f"Участников: {participants_count}. Победителей будет выбрано: {giveaway.winner_count}.\n\n"
        f"Текст объявления: \n«{announcement}»\n\n"
        "После подтверждения в канал будет отправлено объявление победителя, "
        "а розыгрыш будет завершён. Действие необратимо.\n\n"
        "Подтвердите выбор победителя."
    )


def preview_cancel_giveaway(giveaway: Giveaway) -> str:
    return (
        f"Вы хотите отменить розыгрыш «{giveaway.title}» (id={giveaway.id}) без выбора победителя.\n"
        "Участники останутся в базе, но розыгрыш перейдёт в статус «отменён».\n\n"
        "Подтвердите отмену."
    )


def preview_delete_giveaway(giveaway: Giveaway, participants_count: int) -> str:
    return (
        f"Вы хотите полностью удалить розыгрыш «{giveaway.title}» (id={giveaway.id}) из базы данных.\n"
        f"Будет удалено участников: {participants_count}. Это действие необратимо.\n\n"
        "Подтвердите удаление."
    )


def preview_export_participants(giveaway: Giveaway, participants_count: int) -> str:
    return (
        f"Вы хотите экспортировать список участников розыгрыша «{giveaway.title}» "
        f"(id={giveaway.id}) в CSV-файл.\n"
        f"Участников для экспорта: {participants_count}.\n\n"
        "Подтвердите экспорт."
    )


def preview_participants_list(giveaway: Giveaway, participants_count: int) -> str:
    return (
        f"Показать список участников розыгрыша «{giveaway.title}» (id={giveaway.id})?\n"
        f"Всего участников: {participants_count}."
    )


# ---------- Подробные отчёты после выполнения ----------


def report_new_giveaway(giveaway: Giveaway, channel_username: str) -> str:
    deadline_line = (
        f"Дедлайн: {giveaway.deadline.strftime('%d.%m.%Y %H:%M UTC')}"
        if giveaway.deadline
        else "Дедлайн: не задан"
    )
    return (
        "Розыгрыш опубликован.\n\n"
        f"ID: {giveaway.id}\n"
        f"Название: {giveaway.title}\n"
        f"Канал: @{channel_username}\n"
        f"{deadline_line}\n"
        f"Число победителей: {giveaway.winner_count}\n"
        f"Статус: {giveaway.status.value}"
    )


def report_pick_winner(giveaway: Giveaway, winners: list[Winner]) -> str:
    lines = [
        "Победитель выбран и объявлен в канале.",
        "",
        f"ID розыгрыша: {giveaway.id}",
        f"Название: {giveaway.title}",
        "Победители:",
    ]
    for w in winners:
        name = f"@{w.username}" if w.username else (w.first_name or str(w.user_id))
        lines.append(f"  • {name} (id: {w.user_id})")
    lines.append(f"Статус розыгрыша: {giveaway.status.value}")
    return "\n".join(lines)


def report_cancel_giveaway(giveaway_id: int) -> str:
    return f"Розыгрыш {giveaway_id} отменён. Участники сохранены в базе, победитель не выбирался."


def report_delete_giveaway(giveaway_id: int, participants_count: int) -> str:
    return (
        f"Розыгрыш {giveaway_id} и {participants_count} участник(ов) "
        "безвозвратно удалены из базы данных."
    )


def report_export_participants(giveaway_id: int, participants_count: int) -> str:
    return f"Экспортировано {participants_count} участник(ов) розыгрыша {giveaway_id}."
