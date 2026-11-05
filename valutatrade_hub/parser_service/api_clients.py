"""Клиенты внешних API: CoinGecko (крипта) и ExchangeRate-API (фиат).

Оба клиента возвращают единый словарь {"BTC_USD": 59337.21, ...}.
Ошибки сети/API заворачиваются в ApiRequestError с понятным сообщением.
"""

from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import CONFIG, ParserConfig


class BaseApiClient(ABC):
    """Базовый интерфейс клиента источника курсов."""

    name: str = "BaseApiClient"

    def __init__(self, config: ParserConfig = CONFIG):
        self.config = config

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Получить курсы к базовой валюте. Формат: {"BTC_USD": 59337.21, ...}."""
        raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
    """Криптовалюты через публичное API CoinGecko (без ключа)."""

    name = "CoinGecko"

    def fetch_rates(self) -> dict[str, float]:
        ids = [self.config.CRYPTO_ID_MAP[c] for c in self.config.CRYPTO_CURRENCIES]
        params = {
            "ids": ",".join(ids),
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }
        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"CoinGecko: сетевая ошибка ({exc})")

        if response.status_code == 429:
            raise ApiRequestError("CoinGecko: превышен лимит запросов (429)")
        if response.status_code != 200:
            raise ApiRequestError(
                f"CoinGecko: HTTP {response.status_code} — {response.text[:100]}"
            )

        try:
            payload = response.json()
        except ValueError:
            raise ApiRequestError("CoinGecko: некорректный JSON в ответе")

        base = self.config.BASE_CURRENCY.upper()
        result: dict[str, float] = {}
        for code in self.config.CRYPTO_CURRENCIES:
            cg_id = self.config.CRYPTO_ID_MAP.get(code)
            if not cg_id:
                continue
            entry = payload.get(cg_id)
            if not isinstance(entry, dict):
                continue
            rate = entry.get(base.lower())
            if isinstance(rate, (int, float)) and rate > 0:
                result[f"{code}_{base}"] = float(rate)
        return result


class ExchangeRateApiClient(BaseApiClient):
    """Фиатные валюты через ExchangeRate-API (нужен ключ)."""

    name = "ExchangeRate-API"

    def fetch_rates(self) -> dict[str, float]:
        if not self.config.has_exchangerate_key():
            raise ApiRequestError(
                "ExchangeRate-API: не задан ключ (EXCHANGERATE_API_KEY в .env)"
            )

        base = self.config.BASE_CURRENCY.upper()
        url = f"{self.config.EXCHANGERATE_API_URL}/{self.config.EXCHANGERATE_API_KEY}/latest/{base}"
        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"ExchangeRate-API: сетевая ошибка ({exc})")

        if response.status_code == 429:
            raise ApiRequestError("ExchangeRate-API: превышен лимит запросов (429)")
        if response.status_code != 200:
            raise ApiRequestError(
                f"ExchangeRate-API: HTTP {response.status_code} — {response.text[:100]}"
            )

        try:
            payload = response.json()
        except ValueError:
            raise ApiRequestError("ExchangeRate-API: некорректный JSON в ответе")

        if payload.get("result") != "success":
            error_type = payload.get("error-type", "unknown")
            raise ApiRequestError(f"ExchangeRate-API: {error_type}")

        raw_rates = (
            payload.get("conversion_rates")
            or payload.get("rates")
            or {}
        )
        result: dict[str, float] = {}
        for code in self.config.FIAT_CURRENCIES:
            rate = raw_rates.get(code)
            if isinstance(rate, (int, float)) and rate > 0:
                # API отдаёт "сколько code за 1 base"; нам нужно "сколько base за 1 code"
                result[f"{code}_{base}"] = 1.0 / float(rate)
        return result


def build_clients(source: str | None = None) -> list[BaseApiClient]:
    """Собрать список клиентов для обновления.

    source=None → все; "coingecko" → только CoinGecko; "exchangerate" → только фиат.
    """
    all_clients: list[BaseApiClient] = [CoinGeckoClient(), ExchangeRateApiClient()]
    if source is None:
        return all_clients
    key = source.strip().lower()
    mapping = {"coingecko": CoinGeckoClient, "exchangerate": ExchangeRateApiClient}
    if key not in mapping:
        raise ValueError(f"Неизвестный источник '{source}'. Ожидается coingecko или exchangerate")
    return [mapping[key]()]