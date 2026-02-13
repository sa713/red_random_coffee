from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    db_path: Path
    backup_dir: Path
    backup_retention: int
    timezone: str
    draw_cron: str
    repeat_window_weeks: int
    ready_window_hours: int
    offices: list[str]
    calendar_suggestion_mode: str
    lock_path: Path

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def _parse_admins(value: str) -> set[int]:
    result: set[int] = set()
    if not value:
        return result
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        result.add(int(item))
    return result


def _parse_offices(value: str) -> list[str]:
    items = [x.strip().upper() for x in value.split(",") if x.strip()]
    return items


def load_settings() -> Settings:
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN не задан")

    timezone = os.getenv("TIMEZONE", "Europe/Moscow").strip()
    draw_cron = os.getenv("DRAW_CRON", "MON 11:00").strip()
    offices = _parse_offices(os.getenv("OFFICES", "MSK,SPB"))
    if not offices:
        raise RuntimeError("OFFICES не задан")

    calendar_mode = os.getenv("CALENDAR_SUGGESTION_MODE", "default").strip().lower()
    if calendar_mode not in {"none", "default"}:
        raise RuntimeError("CALENDAR_SUGGESTION_MODE должен быть none или default")

    db_path = Path(os.getenv("DB_PATH", "./data/random_coffee.sqlite")).expanduser()
    backup_dir = Path(os.getenv("BACKUP_DIR", "./data/backups")).expanduser()
    lock_path = Path(os.getenv("LOCK_PATH", "/tmp/random_coffee_draw.lock")).expanduser()

    return Settings(
        bot_token=bot_token,
        admin_ids=_parse_admins(os.getenv("ADMINS", "")),
        db_path=db_path,
        backup_dir=backup_dir,
        backup_retention=int(os.getenv("BACKUP_RETENTION", "30")),
        timezone=timezone,
        draw_cron=draw_cron,
        repeat_window_weeks=int(os.getenv("REPEAT_WINDOW_WEEKS", "8")),
        ready_window_hours=int(os.getenv("READY_WINDOW_HOURS", "24")),
        offices=offices,
        calendar_suggestion_mode=calendar_mode,
        lock_path=lock_path,
    )
