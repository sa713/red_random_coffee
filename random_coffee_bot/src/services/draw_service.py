from __future__ import annotations

import logging
import shutil
from datetime import datetime, timedelta

import portalocker
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config.settings import Settings
from db.repositories import Repository, User
from matching.algorithm import make_pairs
from scheduler.cron_utils import next_draw_dt, prev_draw_dt, week_id_for_draw
from texts.messages import NO_PAIR, PAIR_MESSAGE, READY_REMINDER
from services.calendar import build_google_calendar_url

logger = logging.getLogger(__name__)


class DrawService:
    def __init__(self, repo: Repository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings

    def get_runtime_draw_cron(self) -> str:
        return self.repo.get_setting("draw_cron") or self.settings.draw_cron

    def get_runtime_offices(self) -> list[str]:
        raw = self.repo.get_setting("offices")
        if not raw:
            return self.settings.offices
        return [x.strip().upper() for x in raw.split(",") if x.strip()]

    def get_next_round(self, now: datetime | None = None):
        now = now or datetime.now(self.settings.tzinfo)
        draw_cron = self.get_runtime_draw_cron()
        draw_at = next_draw_dt(now, draw_cron, self.settings.tzinfo)
        week_id = week_id_for_draw(draw_at)
        return self.repo.get_or_create_round(week_id, draw_at)

    async def maybe_send_reminders(self, bot: Bot) -> None:
        now = datetime.now(self.settings.tzinfo)
        round_rec = self.get_next_round(now)
        if round_rec.reminders_sent_at is not None:
            return

        delta = round_rec.draw_at - now
        if delta.total_seconds() < 0:
            return
        if delta > timedelta(hours=self.settings.ready_window_hours):
            return

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Я участвую ✅", callback_data=f"ready:{round_rec.id}")]]
        )

        users = self.repo.list_active_users()
        for user in users:
            if not user.office:
                continue
            try:
                await bot.send_message(user.user_id, READY_REMINDER, reply_markup=keyboard)
                self.repo.log_message(user.user_id, round_rec.id, "ready_reminder", "sent")
            except Exception as exc:
                logger.exception("Не удалось отправить reminder user_id=%s", user.user_id)
                self.repo.log_message(user.user_id, round_rec.id, "ready_reminder", "error", str(exc))

        self.repo.mark_reminders_sent(round_rec.id)
        logger.info("Отправлены reminder для round_id=%s", round_rec.id)

    def _backup_db(self) -> None:
        self.settings.backup_dir.mkdir(parents=True, exist_ok=True)
        name = datetime.now().strftime("db_%Y%m%d_%H%M%S.sqlite")
        target = self.settings.backup_dir / name
        shutil.copy2(self.settings.db_path, target)

        backups = sorted(self.settings.backup_dir.glob("db_*.sqlite"), key=lambda p: p.name, reverse=True)
        for old in backups[self.settings.backup_retention :]:
            old.unlink(missing_ok=True)

    async def maybe_run_draw(self, bot: Bot) -> None:
        now = datetime.now(self.settings.tzinfo)
        draw_cron = self.get_runtime_draw_cron()
        draw_at = prev_draw_dt(now, draw_cron, self.settings.tzinfo)

        if now - draw_at > timedelta(minutes=10):
            return

        week_id = week_id_for_draw(draw_at)
        round_rec = self.repo.get_or_create_round(week_id, draw_at)
        if round_rec.status == "done":
            return

        self.settings.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with portalocker.Lock(self.settings.lock_path, timeout=0.1):
                if not self.repo.mark_round_running(round_rec.id):
                    logger.info("Round уже обработан round_id=%s", round_rec.id)
                    return

                logger.info("Старт draw round_id=%s week_id=%s", round_rec.id, round_rec.week_id)
                self._backup_db()
                try:
                    await self._run_draw_round(bot, round_rec.id, round_rec.draw_at)
                    self.repo.mark_round_done(round_rec.id)
                except Exception:
                    logger.exception("Ошибка draw round_id=%s", round_rec.id)
                    raise
        except portalocker.exceptions.LockException:
            logger.info("Пропуск draw: lock уже удерживается другим процессом")

    async def _run_draw_round(self, bot: Bot, round_id: int, draw_at: datetime) -> None:
        ready_by_office = self.repo.get_ready_users_by_office(round_id)
        window_start = draw_at - timedelta(weeks=self.settings.repeat_window_weeks)

        for office, users in ready_by_office.items():
            user_ids = [u.user_id for u in users]
            username_by_id = {u.user_id: u.username for u in users}

            recent_pairs = self.repo.get_recent_pairs(office, window_start)
            skip_counts = self.repo.get_skip_counts(office)

            result = make_pairs(user_ids, recent_pairs, skip_counts)
            self.repo.store_pairs(round_id, office, result.pairs, result.repeated_pairs)
            self.repo.store_skipped(round_id, office, result.skipped)

            for a, b in result.pairs:
                ua = username_by_id[a]
                ub = username_by_id[b]
                await self._send_pair_message(bot, round_id, a, ua, ub)
                await self._send_pair_message(bot, round_id, b, ub, ua)

            for uid in result.skipped:
                await self._safe_send(bot, uid, NO_PAIR, round_id, "no_pair")

        self.repo.reset_readiness(round_id)

    async def _send_pair_message(
        self,
        bot: Bot,
        round_id: int,
        user_id: int,
        me_username: str,
        pair_username: str,
    ) -> None:
        url = build_google_calendar_url(
            me_username=me_username,
            pair_username=pair_username,
            mode=self.settings.calendar_suggestion_mode,
            tz=self.settings.tzinfo,
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Добавить в Google Calendar", url=url)]]
        )
        text = PAIR_MESSAGE.format(pair_username=pair_username)
        await self._safe_send(bot, user_id, text, round_id, "pair", keyboard)

    async def _safe_send(
        self,
        bot: Bot,
        user_id: int,
        text: str,
        round_id: int | None,
        msg_type: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        try:
            await bot.send_message(user_id, text, reply_markup=reply_markup)
            self.repo.log_message(user_id, round_id, msg_type, "sent")
        except Exception as exc:
            logger.exception("send_message error user_id=%s type=%s", user_id, msg_type)
            self.repo.log_message(user_id, round_id, msg_type, "error", str(exc))
