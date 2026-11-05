from valutatrade_hub.core.usecases import list_rates, list_users


def run_cli() -> None:
    print("ValutaTrade Hub")
    print("Rates:", list_rates())
    print("Users:", list_users())
