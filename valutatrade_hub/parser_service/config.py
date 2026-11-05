"""Конфигурация Parser Service: эндпоинты, списки валют, ключи.

API-ключ загружается из переменной окружения EXCHANGERATE_API_KEY
или из файла .env в корне проекта (не коммитится в git).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


_DOTENV = _load_dotenv(PROJECT_ROOT / ".env")


def _get_env(key: str, default: str = "") -> str:
    return os.getenv(key) or _DOTENV.get(key, default)


@dataclass(frozen=True)
class ParserConfig:
    """Настройки Parser Service. Значения по умолчанию можно переопределить."""

    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: _get_env("EXCHANGERATE_API_KEY", "")
    )

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    RATES_FILE_PATH: str = str(PROJECT_ROOT / "data" / "rates.json")
    HISTORY_FILE_PATH: str = str(PROJECT_ROOT / "data" / "exchange_rates.json")

    REQUEST_TIMEOUT: int = 10

    def has_exchangerate_key(self) -> bool:
        return bool(self.EXCHANGERATE_API_KEY and self.EXCHANGERATE_API_KEY.strip())


CONFIG = ParserConfig()