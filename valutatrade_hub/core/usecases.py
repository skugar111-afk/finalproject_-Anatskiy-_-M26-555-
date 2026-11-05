"""Бизнес-логика ValutaTrade Hub: регистрация, логин, операции, курсы.

Использует:
- DatabaseManager (Singleton) — доступ к JSON-хранилищу;
- SettingsLoader (Singleton) — TTL курсов, базовая валюта;
- @log_action — логирование BUY/SELL/REGISTER/LOGIN;
- кастомные исключения (CurrencyNotFoundError, InsufficientFundsError, ApiRequestError).
"""

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import validate_currency
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import get_database
from valutatrade_hub.infra.settings import SettingsLoader


db = get_database()
settings = SettingsLoader()

_current_user = None


# ---------- сессия ----------

def get_current_user():
    global _current_user
    if _current_user is not None:
        return _current_user
    data = db.read_json("session.json", default={})
    user_id = data.get("user_id") if isinstance(data, dict) else None
    if user_id is None:
        return None
    for record in _load_users():
        if int(record.get("user_id", -1)) == int(user_id):
            _current_user = User.from_dict(record)
            return _current_user
    return None


def set_current_user(user):
    global _current_user
    _current_user = user
    if user is None:
        db.save("session.json", {})
    else:
        db.save("session.json", {"user_id": user.user_id})


def require_login():
    user = get_current_user()
    if user is None:
        raise RuntimeError("Сначала выполните login")
    return user


# ---------- users.json ----------

def _load_users():
    return db.load_list("users.json")


def _save_users(users):
    db.save("users.json", users)


def _next_user_id(users):
    if not users:
        return 1
    return max(int(u.get("user_id", 0)) for u in users) + 1


# ---------- portfolios.json ----------

def _load_portfolios():
    return db.load_list("portfolios.json")


def _save_portfolios(items):
    db.save("portfolios.json", items)


def _find_portfolio(user_id):
    for item in _load_portfolios():
        if int(item.get("user_id", -1)) == user_id:
            return item
    return None


def _save_portfolio(portfolio):
    items = _load_portfolios()
    for i, item in enumerate(items):
        if int(item.get("user_id", -1)) == portfolio.user_id:
            items[i] = portfolio.to_dict()
            break
    else:
        items.append(portfolio.to_dict())
    _save_portfolios(items)


# ---------- rates.json ----------

def _load_rates():
    return db.load_dict("rates.json")


def _pair_code(f, t):
    return f"{f}_{t}"


def get_rate(from_code, to_code):
    """Курс from→to из кеша rates.json.

    Бросает CurrencyNotFoundError на неизвестный код,
    ApiRequestError если курса нет в кеше и обновить не удалось.
    TTL из SettingsLoader зарезервирован для ParserService (в учебной версии
    курсы считаются актуальными, пока присутствуют в кеше).
    """
    f = validate_currency(from_code)
    t = validate_currency(to_code)
    if f == t:
        return {"rate": 1.0, "updated_at": None}

    rates = _load_rates()

    direct = rates.get(_pair_code(f, t))
    if isinstance(direct, dict) and "rate" in direct:
        return {"rate": float(direct["rate"]), "updated_at": direct.get("updated_at")}

    reverse = rates.get(_pair_code(t, f))
    if isinstance(reverse, dict) and float(reverse.get("rate", 0)) != 0:
        return {
            "rate": 1.0 / float(reverse["rate"]),
            "updated_at": reverse.get("updated_at"),
        }

    raise ApiRequestError(f"курс {f}→{t} недоступен, повторите позже")


# ---------- регистрация / логин ----------

@log_action("REGISTER")
def register(username, password):
    username = (username or "").strip()
    if not username:
        raise ValueError("Имя пользователя не может быть пустым")
    if not password or len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = _load_users()
    if any(u.get("username") == username for u in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = _next_user_id(users)
    user = User.create(user_id, username, password)

    users.append(user.to_dict())
    _save_users(users)

    portfolio = Portfolio(user_id=user_id, user=user)
    _save_portfolio(portfolio)

    return {"user_id": user_id, "username": username}


@log_action("LOGIN")
def login(username, password):
    username = (username or "").strip()
    users = _load_users()
    record = next((u for u in users if u.get("username") == username), None)
    if record is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    user = User.from_dict(record)
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    set_current_user(user)
    return {"user_id": user.user_id, "username": user.username}


# ---------- портфель ----------

def _load_current_portfolio():
    user = require_login()
    item = _find_portfolio(user.user_id) or {"user_id": user.user_id, "wallets": {}}
    portfolio = Portfolio.from_dict(item)
    portfolio._user = user
    return portfolio


def show_portfolio(base="USD"):
    require_login()
    base = validate_currency(base or "USD")
    portfolio = _load_current_portfolio()
    if not portfolio.wallets:
        return []
    rows = []
    total = 0.0
    for code, wallet in portfolio.wallets.items():
        if code == base:
            value = wallet.balance
        else:
            rate = get_rate(code, base)["rate"]
            value = wallet.balance * rate
        total += value
        rows.append(
            {"currency_code": code, "balance": wallet.balance, "value_in_base": value}
        )
    rows.append({"total": total, "base": base})
    return rows


# ---------- buy / sell ----------

def _parse_amount(amount):
    try:
        value = float(amount)
    except (TypeError, ValueError):
        raise ValueError("'amount' должен быть положительным числом")
    if value <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return value


@log_action("BUY", verbose=True)
def _buy_impl(currency_code, amount, user, portfolio):
    code = validate_currency(currency_code)
    value = _parse_amount(amount)

    try:
        rate = get_rate(code, "USD")["rate"]
    except ApiRequestError:
        raise ApiRequestError(f"не удалось получить курс для {code}→USD")

    usd = portfolio.wallets.get("USD")
    cost = value * rate

    if usd is not None and usd.balance > 0 and usd.balance < cost:
        raise InsufficientFundsError(usd.balance, cost, "USD")

    if code not in portfolio.wallets:
        portfolio.add_currency(code)
    wallet = portfolio.get_wallet(code)
    before = wallet.balance
    wallet.deposit(value)
    after = wallet.balance

    if usd is not None and usd.balance > 0:
        usd.withdraw(cost)

    _save_portfolio(portfolio)

    return {
        "currency": code,
        "amount": value,
        "rate": rate,
        "before": before,
        "after": after,
        "cost_usd": cost,
    }


def buy(currency_code, amount):
    user = require_login()
    portfolio = _load_current_portfolio()
    return _buy_impl(
        currency_code=currency_code,
        amount=amount,
        user=user,
        portfolio=portfolio,
    )


@log_action("SELL", verbose=True)
def _sell_impl(currency_code, amount, user, portfolio):
    code = validate_currency(currency_code)
    value = _parse_amount(amount)

    try:
        rate = get_rate(code, "USD")["rate"]
    except ApiRequestError:
        raise ApiRequestError(f"не удалось получить курс для {code}→USD")

    if code not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            f"она создаётся автоматически при первой покупке."
        )

    wallet = portfolio.get_wallet(code)
    before = wallet.balance
    wallet.withdraw(value)  # InsufficientFundsError, если не хватает
    after = wallet.balance

    usd = portfolio.wallets.get("USD")
    revenue = value * rate
    if usd is not None:
        usd.deposit(revenue)

    _save_portfolio(portfolio)

    return {
        "currency": code,
        "amount": value,
        "rate": rate,
        "before": before,
        "after": after,
        "revenue_usd": revenue,
    }


def sell(currency_code, amount):
    user = require_login()
    portfolio = _load_current_portfolio()
    return _sell_impl(
        currency_code=currency_code,
        amount=amount,
        user=user,
        portfolio=portfolio,
    )