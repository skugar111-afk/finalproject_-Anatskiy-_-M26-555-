"""Декоратор @log_action: трассировка доменных операций."""

import functools
from datetime import datetime
from typing import Any, Callable

from valutatrade_hub.logging_config import get_logger

logger = get_logger()


def _extract_user(args: tuple, kwargs: dict) -> str:
    """Достать username: явный kwargs, объект user, либо первый позиционный."""
    if "username" in kwargs:
        return str(kwargs["username"])
    user_obj = kwargs.get("user")
    if user_obj is not None:
        return str(getattr(user_obj, "username", user_obj))
    if args:
        first = args[0]
        if isinstance(first, str):
            return first
        if hasattr(first, "username"):
            return str(first.username)
    return "anonymous"


def _extract_currency(kwargs: dict) -> Any:
    return kwargs.get("currency_code") or kwargs.get("currency")


def log_action(action: str, verbose: bool = False) -> Callable:
    """Логирует вызов функции на уровне INFO и пробрасывает исключения дальше.

    action — BUY/SELL/REGISTER/LOGIN.
    verbose — добавлять ли before/after из результата.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            username = _extract_user(args, kwargs)
            currency = _extract_currency(kwargs)
            amount = kwargs.get("amount")
            base = kwargs.get("base") or "USD"
            ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                logger.error(
                    "%s user=%r currency=%r amount=%r result=ERROR "
                    "error_type=%s error=%r",
                    action,
                    username,
                    currency,
                    amount,
                    type(exc).__name__,
                    str(exc),
                )
                raise

            rate = None
            extra = ""
            if isinstance(result, dict):
                rate = result.get("rate")
                if verbose:
                    before = result.get("before")
                    after = result.get("after")
                    if before is not None or after is not None:
                        extra = f" before={before} after={after}"

            logger.info(
                "%s user=%r currency=%r amount=%r rate=%r base=%r result=OK%s ts=%s",
                action,
                username,
                currency,
                amount,
                rate,
                base,
                extra,
                ts,
            )
            return result

        return wrapper

    return decorator