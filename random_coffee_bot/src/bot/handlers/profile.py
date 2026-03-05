from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.context import AppContext
from bot.keyboards import back_to_menu_keyboard, menu_keyboard, offices_keyboard


def _status_text(ctx: AppContext, user_id: int) -> str:
    user = ctx.repo.get_user(user_id)
    if not user:
        return "Ты пока не зарегистрирован. Нажми /start."

    next_round = ctx.draw_service.get_next_round()
    ready = ctx.repo.is_ready(user.user_id, next_round.id)
    participate_text = "участвую" if ready else "не участвую"
    return "\n".join(
        [
            "Статус профиля:",
            "- Зарегистрирован: да",
            f"- Офис: {user.office or 'не задан'}",
            f"- Активен: {'да' if user.is_active else 'нет'}",
            f"- В следующем раунде: {participate_text}",
        ]
    )


def build_router(ctx: AppContext) -> Router:
    router = Router(name="profile")

    @router.message(Command("status"), F.chat.type == "private")
    async def status_cmd(message: Message) -> None:
        user = ctx.repo.get_user(message.from_user.id)
        if not user:
            await message.answer("Ты пока не зарегистрирован. Нажми /start.")
            return
        await message.answer(_status_text(ctx, message.from_user.id), reply_markup=back_to_menu_keyboard())

    @router.message(Command("menu"), F.chat.type == "private")
    async def menu_cmd(message: Message) -> None:
        user = ctx.repo.get_user(message.from_user.id)
        if not user:
            await message.answer("Сначала зарегистрируйся через /start.")
            return
        await message.answer("Главное меню:", reply_markup=menu_keyboard(user.is_active))

    @router.message(Command("office"), F.chat.type == "private")
    async def office_cmd(message: Message) -> None:
        user = ctx.repo.get_user(message.from_user.id)
        if not user:
            await message.answer("Сначала зарегистрируйся через /start.")
            return

        offices = ctx.draw_service.get_runtime_offices()
        await message.answer(
            "Выбери новый офис:",
            reply_markup=offices_keyboard(offices, prefix="setoffice", with_menu=True),
        )

    @router.callback_query(F.data == "menu:open")
    async def menu_open(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return
        user = ctx.repo.get_user(callback.from_user.id)
        if not user:
            await callback.message.answer("Сначала зарегистрируйся через /start.")
            await callback.answer()
            return
        await callback.message.answer("Главное меню:", reply_markup=menu_keyboard(user.is_active))
        await callback.answer()

    @router.callback_query(F.data == "menu:status")
    async def menu_status(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return
        await callback.message.answer(_status_text(ctx, callback.from_user.id), reply_markup=back_to_menu_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "menu:office")
    async def menu_office(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return
        user = ctx.repo.get_user(callback.from_user.id)
        if not user:
            await callback.message.answer("Сначала зарегистрируйся через /start.")
            await callback.answer()
            return
        offices = ctx.draw_service.get_runtime_offices()
        await callback.message.answer(
            "Выбери офис:",
            reply_markup=offices_keyboard(offices, prefix="setoffice", with_menu=True),
        )
        await callback.answer()

    @router.callback_query(F.data == "menu:rules")
    async def menu_rules(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return
        await callback.message.answer(ctx.rules_text, reply_markup=back_to_menu_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "menu:leave")
    async def menu_leave(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return
        user = ctx.repo.get_user(callback.from_user.id)
        if not user:
            await callback.message.answer("Сначала зарегистрируйся через /start.")
            await callback.answer()
            return
        ctx.repo.set_user_active(callback.from_user.id, False)
        await callback.message.answer("Ок, участие приостановлено.", reply_markup=back_to_menu_keyboard())
        await callback.answer("Готово")

    @router.callback_query(F.data == "menu:join")
    async def menu_join(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return
        tg_user = callback.from_user
        if not tg_user.username:
            await callback.message.answer(
                "Для участия нужен username. Укажи его в Telegram и повтори /join.",
                reply_markup=back_to_menu_keyboard(),
            )
            await callback.answer()
            return

        db_user = ctx.repo.get_user(tg_user.id)
        if db_user is None:
            ctx.repo.upsert_user(tg_user.id, tg_user.username, None, is_active=True)
        else:
            ctx.repo.upsert_user(tg_user.id, tg_user.username, db_user.office, is_active=True)

        db_user = ctx.repo.get_user(tg_user.id)
        if db_user and db_user.office:
            await callback.message.answer(
                f"Снова в игре. Офис: {db_user.office}",
                reply_markup=back_to_menu_keyboard(),
            )
        else:
            offices = ctx.draw_service.get_runtime_offices()
            await callback.message.answer(
                "Выбери офис:",
                reply_markup=offices_keyboard(offices, prefix="setoffice", with_menu=True),
            )
        await callback.answer("Готово")

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
        await callback.message.answer(
            f"Офис обновлён: {office}",
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()

    @router.message(Command("leave"), F.chat.type == "private")
    async def leave_cmd(message: Message) -> None:
        user = ctx.repo.get_user(message.from_user.id)
        if not user:
            await message.answer("Ты не зарегистрирован. Нажми /start.")
            return
        ctx.repo.set_user_active(message.from_user.id, False)
        await message.answer("Ок, ты вышел из жеребьёвки. История сохранена.", reply_markup=back_to_menu_keyboard())

    @router.message(Command("join"), F.chat.type == "private")
    async def join_cmd(message: Message) -> None:
        user = message.from_user
        if not user.username:
            await message.answer(
                "Для участия нужен username. Укажи его в Telegram и повтори /join.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        db_user = ctx.repo.get_user(user.id)
        if db_user is None:
            ctx.repo.upsert_user(user.id, user.username, None, is_active=True)
        else:
            ctx.repo.upsert_user(user.id, user.username, db_user.office, is_active=True)

        db_user = ctx.repo.get_user(user.id)
        if db_user and db_user.office:
            await message.answer(f"Снова в игре. Офис: {db_user.office}", reply_markup=back_to_menu_keyboard())
        else:
            offices = ctx.draw_service.get_runtime_offices()
            await message.answer(
                "Выбери офис:",
                reply_markup=offices_keyboard(offices, prefix="setoffice", with_menu=True),
            )

    return router
