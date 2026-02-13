from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.draw_service import DrawService

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, bot: Bot, draw_service: DrawService) -> None:
        self.bot = bot
        self.draw_service = draw_service
        self.scheduler = AsyncIOScheduler()

    async def _tick(self) -> None:
        await self.draw_service.maybe_send_reminders(self.bot)
        await self.draw_service.maybe_run_draw(self.bot)

    def start(self) -> None:
        self.scheduler.add_job(
            self._tick,
            IntervalTrigger(minutes=1),
            id="draw_tick",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=50,
        )
        self.scheduler.start()
        logger.info("Планировщик запущен")

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
