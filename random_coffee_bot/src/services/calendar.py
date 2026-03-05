from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo


def _next_weekday_noon(now_local: datetime) -> datetime:
    candidate = now_local.replace(hour=12, minute=0, second=0, microsecond=0)
    if candidate <= now_local:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def build_google_calendar_url(
    me_username: str,
    pair_username: str,
    mode: str,
    tz: ZoneInfo,
) -> str:
    text = f"Random Coffee: @{me_username} + @{pair_username}"
    details = f"Договоритесь о времени и месте в чате: @{pair_username}"
    data = {
        "action": "TEMPLATE",
        "text": text,
        "details": details,
    }

    if mode == "default":
        now = datetime.now(tz)
        start = _next_weekday_noon(now)
        end = start + timedelta(minutes=30)
        start_utc = start.astimezone(ZoneInfo("UTC"))
        end_utc = end.astimezone(ZoneInfo("UTC"))
        data["dates"] = f"{start_utc.strftime('%Y%m%dT%H%M%SZ')}/{end_utc.strftime('%Y%m%dT%H%M%SZ')}"
        data["ctz"] = str(tz)

    # web-ссылка через HTTPS открывается и на Android, и на iOS (в браузере/приложении).
    return "https://www.google.com/calendar/render?" + urlencode(data)
