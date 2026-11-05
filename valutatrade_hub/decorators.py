"""Декоратор @log_action: трассировка доменных операций."""

import functools
from datetime import datetime
from typing import Any, Callable

from valutatrade_hub.logging_config import get_logger

logger = get_logger()


def _extract_user(instance_or_cls, args: tuple, kwargs: dict) -> str:
    user = kwargs.get("username") or kwargs.get("user")
    if user is None and args:
        first = args[0]
        if hasattr(first, "username"):
            user = first.username
    return str(user) if user is not None else "anonymous"


def log_action(action: str, verbose: bool = False) -> Callable:
    """Логирует вызов функции на уровне INFO и пробрасывает исключения дальше.

    action — строка вида BUY/SELL/REGISTER/LOGIN.
    verbose — добавлять ли в лог дополнительный контекст из результата.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            username = _extract_user(None, args, kwargs)
            currency = kwargs.get("currency_code") or kwargs.get("currency")
            amount = kwargs.get("amount")
            if currency is None and len(args) >= 2:
                currency = args[1]
            if amount is None and len(args) >= 3:
                amount = args[2]

            base = kwargs.get("base") or "USD"
            ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                logger.error(
                    "%s user=%r currency=%r amount=%r result=ERROR error_type=%s error=%r",
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