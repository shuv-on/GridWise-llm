"""FastAPI dependency providers."""
from app.config import Settings, get_settings


def settings_dep() -> Settings:
    return get_settings()