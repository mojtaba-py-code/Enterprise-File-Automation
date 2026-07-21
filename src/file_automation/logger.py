"""Central logging configuration.

A single named logger (``file_automation``) is configured once from the
:class:`~file_automation.config.LoggingConfig`. All modules obtain child
loggers via :func:`get_logger` so output is consistent and controlled from one
place.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import LoggingConfig

_ROOT_NAME = "file_automation"
_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(cfg: LoggingConfig) -> logging.Logger:
    """Configure and return the package root logger (idempotent)."""
    logger = logging.getLogger(_ROOT_NAME)
    logger.setLevel(cfg.level)
    logger.propagate = False

    # Reset so repeated calls (e.g. in tests) do not stack handlers.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(_FORMAT)

    if cfg.console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)

    if cfg.file is not None:
        cfg.file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            cfg.file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child of the package root logger."""
    if name is None:
        return logging.getLogger(_ROOT_NAME)
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
