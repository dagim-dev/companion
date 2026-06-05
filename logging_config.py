"""Shared logging setup for API server and CLI."""

from __future__ import annotations

import logging
import os

import config


def configure_logging() -> None:
    default_level = "INFO" if config.ENV == "development" else "WARNING"
    level_name = os.getenv("LOG_LEVEL", default_level).upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )
    for name in ("persistence_policy", "api.main", "uvicorn.error"):
        logging.getLogger(name).setLevel(level)
