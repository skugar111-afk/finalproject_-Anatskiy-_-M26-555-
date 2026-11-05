"""Singleton DatabaseManager: единая абстракция над JSON-хранилищем.

Singleton реализован через __new__ (как и SettingsLoader) — простой,
читаемый способ, гарантирует один экземпляр на процесс и один набор
путей к файлам.
"""

import json
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Чтение/запись JSON-файлов проекта. Один экземпляр на процесс."""

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = SettingsLoader()
        return cls._instance

    # ---------- утилиты ----------

    def _path(self, filename: str) -> Path:
        return Path(self._settings.get("data_dir")) / filename

    def _ensure_data_dir(self) -> None:
        Path(self._settings.get("data_dir")).mkdir(parents=True, exist_ok=True)

    # ---------- низкоуровневые операции ----------

    def read_json(self, filename: str, default: Any = None) -> Any:
        """Прочитать JSON. Если файла нет или он битый — вернуть default."""
        path = self._path(filename)
        if not path.exists():
            return default
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default

    def write_json(self, filename: str, payload: Any) -> None:
        """Атомарно записать JSON (через временный файл)."""
        self._ensure_data_dir()
        path = self._path(filename)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp.replace(path)

    # ---------- удобные обёртки ----------

    def load_list(self, filename: str) -> list:
        data = self.read_json(filename, default=[])
        return data if isinstance(data, list) else []

    def load_dict(self, filename: str) -> dict:
        data = self.read_json(filename, default={})
        return data if isinstance(data, dict) else {}

    def save(self, filename: str, payload: Any) -> None:
        self.write_json(filename, payload)


def get_database() -> DatabaseManager:
    """Удобный доступ к синглтону."""
    return DatabaseManager()