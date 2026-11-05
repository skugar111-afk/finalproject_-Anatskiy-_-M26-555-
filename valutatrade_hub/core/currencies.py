"""Иерархия валют ValutaTrade Hub: ABC Currency + Fiat/Crypto + реестр."""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактная валюта: общий интерфейс для фиата и крипты."""

    def __init__(self, code: str, name: str):
        code = (code or "").strip().upper()
        if not code or not (2 <= len(code) <= 5) or " " in code:
            raise ValueError(
                "Код валюты должен быть 2–5 символов, без пробелов, в верхнем регистре"
            )
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не может быть пустым")
        self.code = code
        self.name = name.strip()

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI и логов."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, name={self.name!r})"


class FiatCurrency(Currency):
    """Фиатная валюта: есть страна/зона эмиссии."""

    def __init__(self, code: str, name: str, issuing_country: str):
        super().__init__(code, name)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("issuing_country не может быть пустым")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта: алгоритм и рыночная капитализация."""

    def __init__(self, code: str, name: str, algorithm: str, market_cap: float):
        super().__init__(code, name)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("algorithm не может быть пустым")
        market_cap = float(market_cap)
        if market_cap < 0:
            raise ValueError("market_cap не может быть отрицательным")
        self.algorithm = algorithm.strip()
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


# ---------- реестр валют ----------

_CURRENCIES: dict[str, Currency] = {
    "USD": FiatCurrency("USD", "US Dollar", "United States"),
    "EUR": FiatCurrency("EUR", "Euro", "Eurozone"),
    "RUB": FiatCurrency("RUB", "Russian Ruble", "Russia"),
    "GBP": FiatCurrency("GBP", "Pound Sterling", "United Kingdom"),
    "BTC": CryptoCurrency("BTC", "Bitcoin", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("ETH", "Ethereum", "Ethash", 4.0e11),
}


def get_currency(code: str) -> Currency:
    """Получить валюту по коду. Бросает CurrencyNotFoundError, если код неизвестен."""
    key = (code or "").strip().upper()
    if not key:
        raise CurrencyNotFoundError(str(code))
    if key not in _CURRENCIES:
        raise CurrencyNotFoundError(key)
    return _CURRENCIES[key]


def list_currency_codes() -> list[str]:
    """Список поддерживаемых кодов — для подсказок в CLI."""
    return sorted(_CURRENCIES.keys())