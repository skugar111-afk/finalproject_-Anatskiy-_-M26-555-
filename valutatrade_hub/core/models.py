from dataclasses import dataclass, field


@dataclass
class User:
    username: str
    wallets: dict[str, float] = field(default_factory=dict)


@dataclass
class Portfolio:
    username: str
    positions: dict[str, float] = field(default_factory=dict)
