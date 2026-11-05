"""Простой планировщик: запускать RatesUpdater.run_update() с интервалом.

Использует threading.Timer — без внешних зависимостей.
Для продакшена лучше APScheduler, но для учебного проекта достаточно.
"""

import threading

from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = get_logger()


class Scheduler:
    """Периодический запуск обновления курсов."""

    def __init__(self, interval_seconds: int = 300, updater: RatesUpdater | None = None):
        self.interval_seconds = max(10, int(interval_seconds))
        self.updater = updater or RatesUpdater()
        self._timer: threading.Timer | None = None
        self._running = False

    def _tick(self) -> None:
        try:
            self.updater.run_update()
        except Exception as exc:
            logger.exception("Scheduler tick failed: %s", exc)
        if self._running:
            self._timer = threading.Timer(self.interval_seconds, self._tick)
            self._timer.daemon = True
            self._timer.start()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("Scheduler started: every %ds", self.interval_seconds)
        self._tick()

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()
        logger.info("Scheduler stopped")