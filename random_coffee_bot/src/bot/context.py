from __future__ import annotations

from dataclasses import dataclass

from config.settings import Settings
from db.repositories import Repository
from services.draw_service import DrawService


@dataclass(slots=True)
class AppContext:
    settings: Settings
    repo: Repository
    draw_service: DrawService
    rules_text: str
