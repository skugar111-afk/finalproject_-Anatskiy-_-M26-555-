"""Singleton SettingsLoader: единая точка конфигурации проекта.

Singleton реализован через __new__ — это самый простой и читаемый способ
в Python: не требует метакласса, легко тестируется, гарантирует ровно один
экземпляр при повторных вызовах SettingsLoader().
"""

from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SettingsLoader:
    """Загружает и кеширует настройки проекта. Один экземпляр на процесс."""

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
            cls._instance._config = {}
        return cls._instance

    # ---------- загрузка ----------

    def _defaults(self) -> dict[str, Any]:
        return {
            "data_dir": str(PROJECT_ROOT / "data"),
            "users_file": str(PROJECT_ROOT / "data" / "users.json"),
            "portfolios_file": str(PROJECT_ROOT / "data" / "portfolios.json"),
            "rates_file": str(PROJECT_ROOT / "data" / "rates.json"),
            "session_file": str(PROJECT_ROOT / "data" / "session.json"),
            "rates_ttl_seconds": 300,
            "default_base_currency": "USD",
            "log_dir": str(PROJECT_ROOT / "logs"),
            "log_file": str(PROJECT_ROOT / "logs" / "actions.log"),
            "log_level": "INFO",
            "log_max_bytes": 1_000_000,
            "log_backup_count": 3,
        }

    def _load(self) -> None:
        config = self._defaults()
        # при желании здесь можно читать pyproject.toml → [tool.valutatrade]
        # и переопределять значения из config.json; пока — только дефолты.
        self._config = config
        self._loaded = True

    # ---------- публичный интерфейс ----------

    def get(self, key: str, default: Any = None) -> Any:
        if not self._loaded:
            self._load()
        return self._config.get(key, default)

    def reload(self) -> None:
        self._loaded = False
        self._load()

    @property
    def data_dir(self) -> Path:
        return Path(self.get("data_dir"))

    @property
    def rates_ttl_seconds(self) -> int:
        return int(self.get("rates_ttl_seconds"))

    @property
    def default_base_currency(self) -> str:
        return str(self.get("default_base_currency"))


def get_settings() -> SettingsLoader:
    """Удобный доступ к синглтону."""
    return SettingsLoader()