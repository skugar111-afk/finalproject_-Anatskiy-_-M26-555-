"""Бизнес-логика ValutaTrade Hub: регистрация, логин, операции, курсы."""

from .models import Portfolio, User, Wallet
from .utils import load_json, save_json

_current_user = None


def get_current_user():
    return _current_user


def set_current_user(user):
    global _current_user
    _current_user = user


def require_login():
    if _current_user is None:
        raise RuntimeError("Сначала выполните login")
    return _current_user


def _load_users():
    raw = load_json("users.json")
    return raw if isinstance(raw, list) else []


def _save_users(users):
    save_json("users.json", users)


def _next_user_id(users):
    if not users:
        return 1
    return max(int(u.get("user_id", 0)) for u in users) + 1


def _load_portfolios():
    raw = load_json("portfolios.json")
    return raw if isinstance(raw, list) else []


def _save_portfolios(items):
    save_json("portfolios.json", items)


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


def _load_rates():
    raw = load_json("rates.json")
    return raw if isinstance(raw, dict) else {}


def _pair_code(f, t):
    return f"{f}_{t}"


def get_rate(from_code, to_code):
    f = (from_code or "").strip().upper()
    t = (to_code or "").strip().upper()
    if not f or not t:
        raise ValueError("Коды валют не могут быть пустыми")
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
    raise ValueError(f"Курс {f}→{t} недоступен. Повторите попытку позже.")


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


def _load_current_portfolio():
    user = require_login()
    item = _find_portfolio(user.user_id) or {"user_id": user.user_id, "wallets": {}}
    portfolio = Portfolio.from_dict(item)
    portfolio._user = user
    return portfolio


def show_portfolio(base="USD"):
    require_login()
    base = (base or "USD").strip().upper()
    portfolio = _load_current_portfolio()
    if not portfolio.wallets:
        return []
    rows = []
    total = 0.0
    for code, wallet in portfolio.wallets.items():
        if code == base:
            value = wallet.balance
        else:
            try:
                rate = get_rate(code, base)["rate"]
            except ValueError:
                raise ValueError(f"Неизвестная базовая валюта '{base}'")
            value = wallet.balance * rate
        total += value
        rows.append(
            {"currency_code": code, "balance": wallet.balance, "value_in_base": value}
        )
    rows.append({"total": total, "base": base})
    return rows


def _parse_amount(amount):
    try:
        value = float(amount)
    except (TypeError, ValueError):
        raise ValueError("'amount' должен быть положительным числом")
    if value <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return value


def buy(currency_code, amount):
    require_login()
    code = (currency_code or "").strip().upper()
    if not code:
        raise ValueError("Код валюты не может быть пустым")
    value = _parse_amount(amount)
    try:
        rate = get_rate(code, "USD")["rate"]
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {code}→USD")
    portfolio = _load_current_portfolio()
    usd = portfolio.wallets.get("USD")
    cost = value * rate
    if usd is not None and usd.balance > 0 and usd.balance < cost:
        raise ValueError(
            f"Недостаточно средств: доступно {usd.balance:.4f} USD, требуется {cost:.2f} USD"
        )
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


def sell(currency_code, amount):
    require_login()
    code = (currency_code or "").strip().upper()
    if not code:
        raise ValueError("Код валюты не может быть пустым")
    value = _parse_amount(amount)
    try:
        rate = get_rate(code, "USD")["rate"]
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {code}→USD")
    portfolio = _load_current_portfolio()
    if code not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: она создаётся автоматически при первой покупке."
        )
    wallet = portfolio.get_wallet(code)
    if value > wallet.balance:
        raise ValueError(
            f"Недостаточно средств: доступно {wallet.balance:.4f} {code}, требуется {value:.4f} {code}"
        )
    before = wallet.balance
    wallet.withdraw(value)
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