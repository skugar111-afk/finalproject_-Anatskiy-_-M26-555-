from .utils import load_json


def list_rates() -> dict:
    return load_json("rates.json")


def list_users() -> list:
    return load_json("users.json")
