from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.context import AppContext
from bot.keyboards import back_to_menu_keyboard, offices_keyboard, start_keyboard
from texts.messages import NEED_USERNAME, WELCOME


def build_router(ctx: AppContext) -> Router:
    router = Router(name="start")

    @router.message(Command("start"), F.chat.type == "private")
    async def start_cmd(message: Message) -> None:
        await message.answer(WELCOME, reply_markup=start_keyboard())

    @router.callback_query(F.data == "start:join")
    async def start_join(callback: CallbackQuery) -> None:
        user = callback.from_user
        if callback.message is None or callback.message.chat.type != "private":
            return
        if not user.username:
            await callback.message.answer(NEED_USERNAME)
            await callback.answer()
            return

        offices = ctx.draw_service.get_runtime_offices()
        await callback.message.answer(
            "Выбери, в каком офисе встретиться за чашкой кофе",
            reply_markup=offices_keyboard(offices, prefix="regoffice"),
        )
        await callback.answer()

    @router.callback_query(F.data == "start:rules")
    async def start_rules(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return
        await callback.message.answer(ctx.rules_text, reply_markup=back_to_menu_keyboard())
        await callback.answer()

    @router.callback_query(F.data.startswith("regoffice:"))
    async def register_office(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return

        office = callback.data.split(":", maxsplit=1)[1].upper()
        offices = set(ctx.draw_service.get_runtime_offices())
        if office not in offices:
            await callback.message.answer("Такого офиса нет в настройках.")
            await callback.answer()
            return

        user = callback.from_user
        if not user.username:
            await callback.message.answer(NEED_USERNAME)
            await callback.answer()
            return

        ctx.repo.upsert_user(user.id, user.username, office, is_active=True)
        await callback.message.answer(
            (
                f"Готово! Раз в неделю буду присылать тебе контакты коллег из {office}.\n"
                "Если захочешь сделать паузу, укажи это в Главном меню."
            ),
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()

    return router
