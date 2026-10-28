"""Конфигурация приложения, загружаемая из переменных окружения."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> list[int]:
    if not raw:
        return []
    result = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if chunk:
            result.append(int(chunk))
    return result


@dataclass(frozen=True)
class Settings:
    bot_token: str
    channel_id: int
    channel_username: str
    initial_admin_ids: list[int] = field(default_factory=list)
    database_path: str = "giveaway_bot.db"
    deadline_check_interval: int = 60

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.database_path}"

    @property
    def channel_invite_link(self) -> str:
        return f"https://t.me/{self.channel_username}"


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "")
    channel_id_raw = os.getenv("CHANNEL_ID", "0")
    channel_username = os.getenv("CHANNEL_USERNAME", "")
    initial_admin_ids = _parse_admin_ids(os.getenv("INITIAL_ADMIN_IDS", ""))
    database_path = os.getenv("DATABASE_PATH", "giveaway_bot.db")
    deadline_check_interval = int(os.getenv("DEADLINE_CHECK_INTERVAL", "60"))

    if not bot_token:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения (.env)")

    return Settings(
        bot_token=bot_token,
        channel_id=int(channel_id_raw),
        channel_username=channel_username,
        initial_admin_ids=initial_admin_ids,
        database_path=database_path,
        deadline_check_interval=deadline_check_interval,
    )
