from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.context import AppContext
from texts.messages import READY_SAVED


def build_router(ctx: AppContext) -> Router:
    router = Router(name="readiness")

    @router.callback_query(F.data.startswith("ready:"))
    async def ready_click(callback: CallbackQuery) -> None:
        if callback.message is None or callback.message.chat.type != "private":
            return

        round_id = int(callback.data.split(":", maxsplit=1)[1])
        round_rec = ctx.draw_service.get_next_round()
        # Разрешаем отмечаться только для ближайшего раунда в окне готовности.
        now = datetime.now(ctx.settings.tzinfo)
        if round_rec.id != round_id:
            await callback.answer("Этот раунд уже неактуален.", show_alert=True)
            return
        if round_rec.draw_at - now > timedelta(hours=ctx.settings.ready_window_hours):
            await callback.answer("Окно готовности ещё не открыто.", show_alert=True)
            return

        user = ctx.repo.get_user(callback.from_user.id)
        if not user or not user.is_active:
            await callback.answer("Сначала зарегистрируйся и включи участие.", show_alert=True)
            return
        if not user.office:
            await callback.answer("Сначала выбери офис через /office.", show_alert=True)
            return

        ctx.repo.set_ready(callback.from_user.id, round_id, True)
        await callback.answer("Принято")
        await callback.message.answer(READY_SAVED)

    return router
