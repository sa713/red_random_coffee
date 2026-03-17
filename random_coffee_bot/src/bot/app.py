from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from bot.context import AppContext
from bot.handlers import admin, profile, readiness, rules, start
from bot.proxy_runtime import get_proxy_enabled
from config.logging_config import setup_logging
from config.settings import load_settings
from db.connection import Database
from db.migrations import migrate
from db.repositories import Repository
from scheduler.jobs import SchedulerService
from services.draw_service import DrawService

logger = logging.getLogger(__name__)


def _load_rules(rules_path: Path) -> str:
    return rules_path.read_text(encoding="utf-8")


def run() -> None:
    asyncio.run(main())


async def main() -> None:
    setup_logging()
    settings = load_settings()

    db = Database(settings.db_path)
    migrate(db)
    repo = Repository(db)

    rules_path = Path(__file__).resolve().parent.parent / "texts" / "rules.md"
    rules_text = _load_rules(rules_path)

    draw_service = DrawService(repo, settings)
    ctx = AppContext(settings=settings, repo=repo, draw_service=draw_service, rules_text=rules_text)

    session = None
    if get_proxy_enabled(settings, repo):
        session = AiohttpSession(proxy=settings.telegram_proxy_url)
        logger.info("Telegram proxy включен.")

    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(start.build_router(ctx))
    dp.include_router(profile.build_router(ctx))
    dp.include_router(readiness.build_router(ctx))
    dp.include_router(rules.build_router(ctx))
    dp.include_router(admin.build_router(ctx))

    scheduler = SchedulerService(bot, draw_service)

    @dp.error()
    async def on_error(event: ErrorEvent) -> bool:
        logger.exception("Unhandled Telegram error: %s", event.exception)
        return True

    scheduler.start()
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
