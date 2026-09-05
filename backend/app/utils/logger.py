"""
Centralized application logger.

Usage:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("message")

Never log secrets, API keys, passwords, tokens, or raw user credentials.
"""

import logging
import sys

from app.core.config import settings

_CONFIGURED = False


def _configure_root_logger() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = logging.DEBUG if settings.debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, configuring the root logger on first use."""
    _configure_root_logger()
    return logging.getLogger(name)
