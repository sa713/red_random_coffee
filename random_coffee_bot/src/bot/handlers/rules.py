from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.context import AppContext


def build_router(ctx: AppContext) -> Router:
    router = Router(name="rules")

    @router.message(Command("rules"), F.chat.type == "private")
    async def rules_cmd(message: Message) -> None:
        await message.answer(ctx.rules_text)

    return router
