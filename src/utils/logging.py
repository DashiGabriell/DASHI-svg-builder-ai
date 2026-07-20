"""Structured logging bootstrap."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config.settings import Settings


def setup_logging(settings: Settings) -> logging.Logger:
    """Configure root + application loggers.

    Creates a rotating file handler under `settings.logs_dir` and a
    coloured-friendly console stream handler.
    """
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file: Path = settings.logs_dir / "svg_builder_ai.log"

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(settings.log_level)
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(settings.log_level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Quieten noisy HTTP libs unless debugging
    if settings.log_level != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    app_logger = logging.getLogger("svg_builder_ai")
    app_logger.info(
        "Logging initialised (level=%s, file=%s)",
        settings.log_level,
        log_file,
    )
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced child logger."""
    return logging.getLogger(f"svg_builder_ai.{name}")
