"""Application entrypoint — boots DI then launches the CustomTkinter UI."""

from __future__ import annotations

import logging
import sys

from src import __app_name__, __version__
from src.config.settings import Settings
from src.core.bootstrap import create_app_context
from src.services.ai import AIService
from src.ui.app import run_app


def main() -> int:
    """Bootstrap services and open the desktop shell.

    Returns:
        Process exit code (0 on success).
    """
    try:
        container = create_app_context()
    except Exception:  # noqa: BLE001
        logging.basicConfig(level=logging.INFO)
        logging.exception("Failed to bootstrap %s", __app_name__)
        return 1

    settings = container.resolve(Settings)
    ai = container.resolve(AIService)
    logger = logging.getLogger("svg_builder_ai.main")

    logger.info("=" * 60)
    logger.info("%s v%s", __app_name__, __version__)
    logger.info("Environment : %s", settings.app_env)
    logger.info("AI enabled  : %s", ai.is_enabled)
    logger.info("AI model    : %s", settings.openrouter_model)
    logger.info("=" * 60)

    try:
        run_app(container)
    except Exception:  # noqa: BLE001
        logger.exception("UI terminated with an error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
