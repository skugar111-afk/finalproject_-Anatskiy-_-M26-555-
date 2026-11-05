"""CLI ValutaTrade Hub: парсер команд, вызовы usecases, форматирование вывода."""

import argparse
import sys

from valutatrade_hub.core import usecases


def _fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def _fmt_amount(value: float) -> str:
    if value == int(value):
        return f"{value:,.0f}"
    return f"{value:,.4f}".rstrip("0").rstrip(".")


def cmd_register(args: argparse.Namespace) -> int:
    try:
        result = usecases.register(args.username, args.password)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"Пользователь '{result['username']}' зарегистрирован (id={result['user_id']}).")
    print(f"Войдите: login --username {result['username']} --password ****")
    return 0


def cmd_login(args: argparse.Namespace) -> int:
    try:
        result = usecases.login(args.username, args.password)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"Вы вошли как '{result['username']}'")
    return 0


def cmd_show_portfolio(args: argparse.Namespace) -> int:
    try:
        rows = usecases.show_portfolio(args.base)
    except (RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1
    if not rows:
        print("Портфель пуст.")
        return 0
    user = usecases.get_current_user()
    base = rows[-1]["base"]
    total = rows[-1]["total"]
    print(f"Портфель пользователя '{user.username}' (база: {base}):")
    for row in rows[:-1]:
        code = row["currency_code"]
        print(
            f"- {code}: {_fmt_amount(row['balance'])}  → "
            f"{_fmt_money(row['value_in_base'])} {base}"
        )
    print("-" * 33)
    print(f"ИТОГО: {_fmt_money(total)} {base}")
    return 0


def cmd_buy(args: argparse.Namespace) -> int:
    try:
        result = usecases.buy(args.currency, args.amount)
    except (RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1
    code = result["currency"]
    print(
        f"Покупка выполнена: {_fmt_amount(result['amount'])} {code} "
        f"по курсу {_fmt_money(result['rate'])} USD/{code}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {code}: было {_fmt_amount(result['before'])} → стало "
        f"{_fmt_amount(result['after'])}"
    )
    print(f"Оценочная стоимость покупки: {_fmt_money(result['cost_usd'])} USD")
    return 0


def cmd_sell(args: argparse.Namespace) -> int:
    try:
        result = usecases.sell(args.currency, args.amount)
    except (RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1
    code = result["currency"]
    print(
        f"Продажа выполнена: {_fmt_amount(result['amount'])} {code} "
        f"по курсу {_fmt_money(result['rate'])} USD/{code}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {code}: было {_fmt_amount(result['before'])} → стало "
        f"{_fmt_amount(result['after'])}"
    )
    print(f"Оценочная выручка: {_fmt_money(result['revenue_usd'])} USD")
    return 0


def cmd_get_rate(args: argparse.Namespace) -> int:
    f = args.from_currency.upper()
    t = args.to_currency.upper()
    try:
        direct = usecases.get_rate(f, t)
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"Курс {f}→{t}: {direct['rate']:.8g} (обновлено: {direct['updated_at'] or '—'})")
    if f != t:
        try:
            reverse = usecases.get_rate(t, f)
            print(f"Обратный курс {t}→{f}: {reverse['rate']:.8g}")
        except ValueError:
            pass
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valutatrade", description="ValutaTrade Hub CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_reg = sub.add_parser("register", help="Зарегистрировать пользователя")
    p_reg.add_argument("--username", required=True)
    p_reg.add_argument("--password", required=True)
    p_reg.set_defaults(func=cmd_register)

    p_login = sub.add_parser("login", help="Войти")
    p_login.add_argument("--username", required=True)
    p_login.add_argument("--password", required=True)
    p_login.set_defaults(func=cmd_login)

    p_show = sub.add_parser("show-portfolio", help="Показать портфель")
    p_show.add_argument("--base", default="USD")
    p_show.set_defaults(func=cmd_show_portfolio)

    p_buy = sub.add_parser("buy", help="Купить валюту")
    p_buy.add_argument("--currency", required=True)
    p_buy.add_argument("--amount", required=True, type=float)
    p_buy.set_defaults(func=cmd_buy)

    p_sell = sub.add_parser("sell", help="Продать валюту")
    p_sell.add_argument("--currency", required=True)
    p_sell.add_argument("--amount", required=True, type=float)
    p_sell.set_defaults(func=cmd_sell)

    p_rate = sub.add_parser("get-rate", help="Курс валюты")
    p_rate.add_argument("--from", dest="from_currency", required=True)
    p_rate.add_argument("--to", dest="to_currency", required=True)
    p_rate.set_defaults(func=cmd_get_rate)

    return parser


def run_cli(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def main() -> None:
    sys.exit(run_cli())