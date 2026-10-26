from fastapi import Request

from app.settings import Settings
from app.state import AppState


def coach(request: Request) -> AppState:
    return request.app.state.coach


def settings(request: Request) -> Settings:
    return request.app.state.settings
