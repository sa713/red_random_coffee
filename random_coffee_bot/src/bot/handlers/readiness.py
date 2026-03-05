from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.context import AppContext
from bot.keyboards import back_to_menu_keyboard
from texts.messages import READY_SAVED, READY_SKIPPED


def build_router(ctx: AppContext) -> Router:
    router = Router(name="readiness")

    async def _validate(callback: CallbackQuery, round_id: int) -> bool:
        if callback.message is None or callback.message.chat.type != "private":
            return False
        round_rec = ctx.draw_service.get_next_round()
        now = datetime.now(ctx.settings.tzinfo)
        if round_rec.id != round_id:
            await callback.answer("Этот раунд уже неактуален.", show_alert=True)
            return False
        if round_rec.draw_at - now > timedelta(hours=ctx.settings.ready_window_hours):
            await callback.answer("Окно готовности ещё не открыто.", show_alert=True)
            return False

        user = ctx.repo.get_user(callback.from_user.id)
        if not user or not user.is_active:
            await callback.answer("Сначала зарегистрируйся и включи участие.", show_alert=True)
            return False
        if not user.office:
            await callback.answer("Сначала выбери офис через /office.", show_alert=True)
            return False
        return True

    @router.callback_query(F.data.startswith("ready:"))
    async def ready_click(callback: CallbackQuery) -> None:
        round_id = int(callback.data.split(":", maxsplit=1)[1])
        if not await _validate(callback, round_id):
            return

        ctx.repo.set_ready(callback.from_user.id, round_id, True)
        await callback.answer("Принято")
        await callback.message.answer(READY_SAVED, reply_markup=back_to_menu_keyboard())

    @router.callback_query(F.data.startswith("ready_skip:"))
    async def ready_skip_click(callback: CallbackQuery) -> None:
        round_id = int(callback.data.split(":", maxsplit=1)[1])
        if not await _validate(callback, round_id):
            return

        ctx.repo.set_ready(callback.from_user.id, round_id, False)
        await callback.answer("Принято")
        await callback.message.answer(READY_SKIPPED, reply_markup=back_to_menu_keyboard())

    return router
