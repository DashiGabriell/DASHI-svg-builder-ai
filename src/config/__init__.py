"""Central configuration package.

Loads environment variables via pydantic-settings and exposes a typed
`Settings` object that the DI container injects throughout the app.
"""

from src.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
