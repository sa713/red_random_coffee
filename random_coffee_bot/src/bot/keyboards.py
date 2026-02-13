from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Участвовать", callback_data="start:join")],
            [InlineKeyboardButton(text="Правила", callback_data="start:rules")],
        ]
    )


def offices_keyboard(offices: list[str], prefix: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=office, callback_data=f"{prefix}:{office}")] for office in offices]
    return InlineKeyboardMarkup(inline_keyboard=rows)
