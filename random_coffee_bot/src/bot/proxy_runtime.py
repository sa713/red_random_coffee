from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

from config.settings import Settings
from db.repositories import Repository

logger = logging.getLogger(__name__)

PROXY_SETTING_KEY = "telegram_proxy_enabled"


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    raw = value.strip().lower()
    if raw in {"1", "true", "on", "yes", "y"}:
        return True
    if raw in {"0", "false", "off", "no", "n"}:
        return False
    return None


def get_proxy_enabled(settings: Settings, repo: Repository) -> bool:
    default_enabled = bool(settings.telegram_proxy_url)
    stored = _parse_bool(repo.get_setting(PROXY_SETTING_KEY))
    if stored is None:
        return default_enabled
    if stored and not settings.telegram_proxy_url:
        return False
    return stored


def proxy_status_line(settings: Settings, repo: Repository) -> str:
    configured = bool(settings.telegram_proxy_url)
    enabled = get_proxy_enabled(settings, repo)
    return f"Прокси URL: {'задан' if configured else 'не задан'}\nПрокси режим: {'включён' if enabled else 'выключен'}"


async def apply_proxy_mode(bot: Bot, settings: Settings, enabled: bool) -> tuple[bool, str]:
    if enabled and not settings.telegram_proxy_url:
        return False, "Нельзя включить прокси: TELEGRAM_PROXY_URL не задан в .env"

    new_session = AiohttpSession(proxy=settings.telegram_proxy_url) if enabled else AiohttpSession()

    old_session = getattr(bot, "session", None)
    try:
        bot.session = new_session
    except Exception as exc:
        await new_session.close()
        logger.exception("Не удалось применить proxy mode в рантайме")
        return False, f"Режим сохранён, но не применён в рантайме: {exc}. Нужен restart сервиса."

    if old_session is not None:
        try:
            await old_session.close()
        except Exception:
            logger.exception("Не удалось закрыть старую Telegram session")

    return True, "Режим применён без рестарта."
