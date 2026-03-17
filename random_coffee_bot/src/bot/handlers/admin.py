from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.context import AppContext
from bot.proxy_runtime import PROXY_SETTING_KEY, apply_proxy_mode, get_proxy_enabled, proxy_status_line
from scheduler.cron_utils import normalize_cron


HELP_TEXT = """/admin help
/admin schedule
/admin schedule set <cron|DOW HH:MM>
/admin offices
/admin offices set <MSK,SPB,...>
/admin users add <user_id> <office>
/admin users remove <user_id>
/admin proxy status
/admin proxy on
/admin proxy off
/admin stats"""


def build_router(ctx: AppContext) -> Router:
    router = Router(name="admin")

    def is_admin(user_id: int) -> bool:
        return user_id in ctx.settings.admin_ids

    @router.message(Command("admin"), F.chat.type == "private")
    async def admin_cmd(message: Message) -> None:
        if not is_admin(message.from_user.id):
            await message.answer("Недостаточно прав.")
            return

        parts = (message.text or "").split()
        if len(parts) == 1 or parts[1] == "help":
            await message.answer(HELP_TEXT)
            return

        if parts[1] == "schedule":
            if len(parts) == 2:
                draw_cron = ctx.draw_service.get_runtime_draw_cron()
                await message.answer(
                    f"Текущее расписание:\nDRAW_CRON={draw_cron}\nTIMEZONE={ctx.settings.timezone}"
                )
                return

            raw = (message.text or "")
            token = "/admin schedule set "
            if token not in raw:
                await message.answer("Используй: /admin schedule set <cron|DOW HH:MM>")
                return
            value = raw.split(token, maxsplit=1)[1].strip()
            try:
                normalize_cron(value)
            except ValueError as exc:
                await message.answer(str(exc))
                return
            ctx.repo.set_setting("draw_cron", value)
            await message.answer(f"Расписание обновлено: {value}")
            return

        if parts[1] == "offices":
            if len(parts) == 2:
                offices = ",".join(ctx.draw_service.get_runtime_offices())
                await message.answer(f"Офисы: {offices}")
                return

            raw = (message.text or "")
            token = "/admin offices set "
            if token not in raw:
                await message.answer("Используй: /admin offices set <MSK,SPB,...>")
                return
            value = raw.split(token, maxsplit=1)[1].strip().upper()
            offices = [x.strip() for x in value.split(",") if x.strip()]
            if not offices:
                await message.answer("Список офисов пуст.")
                return
            ctx.repo.set_setting("offices", ",".join(offices))
            await message.answer(f"Офисы обновлены: {', '.join(offices)}")
            return

        if parts[1] == "users":
            if len(parts) < 4:
                await message.answer("Используй: /admin users add <user_id> <office> или /admin users remove <user_id>")
                return

            action = parts[2]
            if action == "add" and len(parts) >= 5:
                user_id = int(parts[3])
                office = parts[4].upper()
                if office not in set(ctx.draw_service.get_runtime_offices()):
                    await message.answer("Такого офиса нет в настройках.")
                    return
                existing = ctx.repo.get_user(user_id)
                username = existing.username if existing else f"user_{user_id}"
                ctx.repo.upsert_user(user_id, username, office, is_active=True)
                await message.answer(f"Пользователь {user_id} активирован в офисе {office}.")
                return

            if action == "remove":
                user_id = int(parts[3])
                existing = ctx.repo.get_user(user_id)
                if not existing:
                    await message.answer("Пользователь не найден.")
                    return
                ctx.repo.set_user_active(user_id, False)
                await message.answer(f"Пользователь {user_id} деактивирован.")
                return

            await message.answer("Неизвестная команда users.")
            return

        if parts[1] == "stats":
            next_round = ctx.draw_service.get_next_round()
            last_round = ctx.repo.get_last_done_round()
            stat = ctx.repo.stats(next_round.id, last_round.id if last_round else None)
            by_office = ctx.repo.count_by_office()
            office_text = "\n".join(f"- {office}: {count}" for office, count in sorted(by_office.items())) or "- нет"
            await message.answer(
                "\n".join(
                    [
                        "Статистика:",
                        f"- Всего пользователей: {stat['total']}",
                        f"- Активных: {stat['active']}",
                        "- По офисам:",
                        office_text,
                        f"- Готовых к следующему раунду: {stat['ready_next']}",
                        f"- Пар в последнем раунде: {stat['last_pairs']}",
                        f"- Пропустивших в последнем раунде: {stat['last_skipped']}",
                    ]
                )
            )
            return

        if parts[1] == "proxy":
            action = parts[2].lower() if len(parts) >= 3 else "status"
            if action == "status":
                await message.answer(proxy_status_line(ctx.settings, ctx.repo))
                return
            if action not in {"on", "off"}:
                await message.answer("Используй: /admin proxy status|on|off")
                return

            enabled = action == "on"
            ctx.repo.set_setting(PROXY_SETTING_KEY, "1" if enabled else "0")

            if enabled and not ctx.settings.telegram_proxy_url:
                await message.answer(
                    "Режим сохранён как ON, но TELEGRAM_PROXY_URL не задан в .env.\n"
                    "Добавь URL прокси и перезапусти сервис."
                )
                return

            ok, details = await apply_proxy_mode(message.bot, ctx.settings, enabled)
            mode_text = "включен" if get_proxy_enabled(ctx.settings, ctx.repo) else "выключен"
            await message.answer(f"Прокси режим: {mode_text}.\n{details}")
            return

        await message.answer("Неизвестная админ-команда. Используй /admin help")

    return router
