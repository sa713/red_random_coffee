from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Участвовать", callback_data="start:join")],
            [InlineKeyboardButton(text="Правила", callback_data="start:rules")],
            [InlineKeyboardButton(text="В меню", callback_data="menu:open")],
        ]
    )


def offices_keyboard(offices: list[str], prefix: str, with_menu: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=office, callback_data=f"{prefix}:{office}")] for office in offices]
    if with_menu:
        rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ready_keyboard(round_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да, участвую", callback_data=f"ready:{round_id}")],
            [InlineKeyboardButton(text="Нет, пропущу", callback_data=f"ready_skip:{round_id}")],
            [InlineKeyboardButton(text="В меню", callback_data="menu:open")],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="В меню", callback_data="menu:open")]]
    )


def menu_keyboard(is_active: bool) -> InlineKeyboardMarkup:
    action_label = "Поставить на паузу" if is_active else "Возобновить участие"
    action_cb = "menu:leave" if is_active else "menu:join"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мой статус", callback_data="menu:status")],
            [InlineKeyboardButton(text="Мой офис", callback_data="menu:office")],
            [InlineKeyboardButton(text="Правила", callback_data="menu:rules")],
            [InlineKeyboardButton(text=action_label, callback_data=action_cb)],
        ]
    )
