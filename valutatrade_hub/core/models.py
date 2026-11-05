import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime


class User:
    """Пользователь системы ValutaTrade Hub."""

    MIN_PASSWORD_LENGTH = 4

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        self._user_id = user_id
        self.username = username  # через сеттер с валидацией
        self._hashed_password = hashed_password
        self._salt = salt
        self.registration_date = registration_date

    # ---------- геттеры ----------

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    # ---------- сеттеры ----------

    @username.setter
    def username(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @registration_date.setter
    def registration_date(self, value: datetime) -> None:
        if not isinstance(value, datetime):
            raise TypeError("registration_date должен быть datetime")
        self._registration_date = value

    # ---------- хеширование ----------

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Односторонний псевдо-хеш: sha256(password + salt)."""
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    @classmethod
    def create(cls, user_id: int, username: str, password: str) -> "User":
        """Создать нового пользователя: сгенерировать соль и хеш пароля."""
        if not password or len(password) < cls.MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Пароль должен быть не короче {cls.MIN_PASSWORD_LENGTH} символов"
            )
        salt = secrets.token_hex(16)
        hashed = cls._hash_password(password, salt)
        return cls(user_id, username, hashed, salt, datetime.now())

    # ---------- методы класса ----------

    def get_user_info(self) -> str:
        """Вернуть информацию о пользователе без пароля (и вывести в консоль)."""
        info = (
            f"ID: {self._user_id}\n"
            f"Имя: {self._username}\n"
            f"Дата регистрации: {self._registration_date:%Y-%m-%d %H:%M:%S}"
        )
        print(info)
        return info

    def change_password(self, new_password: str) -> None:
        """Изменить пароль с пересчётом хеша (соль остаётся прежней)."""
        if not new_password or len(new_password) < self.MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Пароль должен быть не короче {self.MIN_PASSWORD_LENGTH} символов"
            )
        self._hashed_password = self._hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        """Проверить, совпадает ли пароль с сохранённым хешем."""
        return self._hash_password(password, self._salt) == self._hashed_password

    # ---------- сериализация ----------

    def to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )

    def __repr__(self) -> str:
        return f"User(user_id={self._user_id}, username={self._username!r})"


@dataclass
class Portfolio:
    """Портфель пользователя (пока заглушка для следующих задач)."""

    username: str
    positions: dict[str, float] = field(default_factory=dict)
