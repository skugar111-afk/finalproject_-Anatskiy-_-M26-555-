"""Вспомогательные функции: JSON-хранилище, валидация валют, конвертации."""

import json
from pathlib import Path

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import CurrencyNotFoundError

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


# ---------- JSON (низкоуровневые, совместимы со старым кодом) ----------

def load_json(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def save_json(name: str, payload) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / name, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ---------- валидация валют ----------

def normalize_currency_code(code: str) -> str:
    """Привести код к верхнему регистру и проверить, что он не пустой."""
    if not isinstance(code, str):
        raise CurrencyNotFoundError(str(code))
    key = code.strip().upper()
    if not key:
        raise CurrencyNotFoundError(code)
    return key


def validate_currency(code: str) -> str:
    """Проверить код через реестр currencies. Бросает CurrencyNotFoundError."""
    key = normalize_currency_code(code)
    get_currency(key)  # бросит CurrencyNotFoundError, если кода нет
    return key


# ---------- конвертации ----------

def _pair(from_code: str, to_code: str) -> str:
    return f"{from_code}_{to_code}"


def convert_amount(
    amount: float,
    from_code: str,
    to_code: str,
    rates: dict,
) -> float:
    """Сконвертировать amount из from_code в to_code по словарю rates.

    rates — словарь вида {"EUR_USD": {"rate": 1.0786, ...}, ...}.
    Поддерживает прямой курс (FROM_TO) и обратный (TO_FROM, через 1/rate).
    """
    f = validate_currency(from_code)
    t = validate_currency(to_code)
    if f == t:
        return float(amount)

    direct = rates.get(_pair(f, t))
    if isinstance(direct, dict) and "rate" in direct:
        return float(amount) * float(direct["rate"])

    reverse = rates.get(_pair(t, f))
    if isinstance(reverse, dict) and float(reverse.get("rate", 0)) != 0:
        return float(amount) / float(reverse["rate"])

    raise CurrencyNotFoundError(f"{f}→{t}")