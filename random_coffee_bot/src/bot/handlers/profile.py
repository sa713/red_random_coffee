from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.context import AppContext
from bot.keyboards import offices_keyboard


def build_router(ctx: AppContext) -> Router:
    router = Router(name="profile")

    @router.message(Command("status"), F.chat.type == "private")
    async def status_cmd(message: Message) -> None:
        user = ctx.repo.get_user(message.from_user.id)
        if not user:
            await message.answer("Ты пока не зарегистрирован. Нажми /start.")
            return

        next_round = ctx.draw_service.get_next_round()
        ready = ctx.repo.is_ready(user.user_id, next_round.id)
        await message.answer(
            "\n".join(
                [
                    "Статус профиля:",
                    f"- Зарегистрирован: да",
                    f"- Офис: {user.office or 'не задан'}",
                    f"- Активен: {'да' if user.is_active else 'нет'}",
                    f"- Готов к ближайшему раунду: {'да' if ready else 'нет'}",
                ]
            )
        )

    @router.message(Command("office"), F.chat.type == "private")
    async def office_cmd(message: Message) -> None:
        user = ctx.repo.get_user(message.from_user.id)
        if not user:
            await message.answer("Сначала зарегистрируйся через /start.")
            return

        offices = ctx.draw_service.get_runtime_offices()
        await message.answer("Выбери новый офис:", reply_markup=offices_keyboard(offices, prefix="setoffice"))

    @router.callback_query(F.data.startswith("setoffice:"))
    async def set_office(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return
        office = callback.data.split(":", maxsplit=1)[1].upper()
        offices = set(ctx.draw_service.get_runtime_offices())
        if office not in offices:
            await callback.message.answer("Такого офиса нет в настройках.")
            await callback.answer()
            return
        ctx.repo.set_user_office(callback.from_user.id, office)
        await callback.message.answer(f"Офис обновлён: {office}")
        await callback.answer()

    @router.message(Command("leave"), F.chat.type == "private")
    async def leave_cmd(message: Message) -> None:
        user = ctx.repo.get_user(message.from_user.id)
        if not user:
            await message.answer("Ты не зарегистрирован. Нажми /start.")
            return
        ctx.repo.set_user_active(message.from_user.id, False)
        await message.answer("Ок, ты вышел из жеребьёвки. История сохранена.")

    @router.message(Command("join"), F.chat.type == "private")
    async def join_cmd(message: Message) -> None:
        user = message.from_user
        if not user.username:
            await message.answer(
                "Для участия нужен username. Укажи его в Telegram и повтори /join."
            )
            return

        db_user = ctx.repo.get_user(user.id)
        if db_user is None:
            ctx.repo.upsert_user(user.id, user.username, None, is_active=True)
        else:
            ctx.repo.upsert_user(user.id, user.username, db_user.office, is_active=True)

        db_user = ctx.repo.get_user(user.id)
        if db_user and db_user.office:
            await message.answer(f"Снова в игре. Офис: {db_user.office}")
        else:
            offices = ctx.draw_service.get_runtime_offices()
            await message.answer("Выбери офис:", reply_markup=offices_keyboard(offices, prefix="setoffice"))

    return router
