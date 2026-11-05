"""Настройка логирования: формат, уровень, ротация.

Формат выбран человекочитаемый (не JSON): проще для проверки в учебном
проекте. При необходимости легко заменить на JSON-форматтер.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

LOG_FORMAT = "%(levelname)s %(asctime)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_configured = False


def setup_logging(level: str | None = None, force: bool = False) -> logging.Logger:
    """Инициализировать логгер проекта (один раз на процесс)."""
    global _configured
    logger = logging.getLogger("valutatrade")
    if _configured and not force:
        return logger

    settings = SettingsLoader()
    log_level = (level or settings.get("log_level", "INFO")).upper()
    log_file = Path(settings.get("log_file"))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=int(settings.get("log_max_bytes", 1_000_000)),
        backupCount=int(settings.get("log_backup_count", 3)),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    _configured = True
    return logger


def get_logger() -> logging.Logger:
    """Получить логгер проекта (с автоинициализацией)."""
    return setup_logging()