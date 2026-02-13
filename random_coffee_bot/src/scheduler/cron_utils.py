from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from croniter import croniter


DOW_MAP = {
    "MON": "1",
    "TUE": "2",
    "WED": "3",
    "THU": "4",
    "FRI": "5",
    "SAT": "6",
    "SUN": "0",
}


def normalize_cron(expr: str) -> str:
    raw = expr.strip().upper()
    parts = raw.split()
    if len(parts) == 2 and ":" in parts[1]:
        dow = DOW_MAP.get(parts[0], parts[0])
        hh, mm = parts[1].split(":", maxsplit=1)
        return f"{int(mm)} {int(hh)} * * {dow}"
    if len(parts) == 5:
        return expr
    raise ValueError("DRAW_CRON должен быть cron (5 полей) или формат DOW HH:MM")


def next_draw_dt(now: datetime, draw_cron: str, tz: ZoneInfo) -> datetime:
    cron_expr = normalize_cron(draw_cron)
    base = now.astimezone(tz)
    return croniter(cron_expr, base).get_next(datetime)


def prev_draw_dt(now: datetime, draw_cron: str, tz: ZoneInfo) -> datetime:
    cron_expr = normalize_cron(draw_cron)
    base = now.astimezone(tz)
    return croniter(cron_expr, base).get_prev(datetime)


def week_id_for_draw(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year}-{iso.week:02d}"
