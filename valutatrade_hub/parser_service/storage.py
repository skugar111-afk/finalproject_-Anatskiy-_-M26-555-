"""Хранилище Parser Service: история exchange_rates.json + кэш rates.json.

exchange_rates.json — список измерений с уникальным id (FROM_TO_ISO_TS).
rates.json — снимок {"pairs": {BTC_USD: {...}}, "last_refresh": ...}.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from valutatrade_hub.parser_service.config import CONFIG, ParserConfig


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


class RatesStorage:
    """Чтение/запись истории и кэша курсов. Атомарные записи."""

    def __init__(self, config: ParserConfig = CONFIG):
        self.config = config
        self.history_path = Path(config.HISTORY_FILE_PATH)
        self.rates_path = Path(config.RATES_FILE_PATH)

    # ---------- история ----------

    def load_history(self) -> list[dict]:
        if not self.history_path.exists():
            return []
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    def append_history(self, records: list[dict]) -> int:
        """Дописать записи с уникальным id, не дублируя существующие."""
        if not records:
            return 0
        history = self.load_history()
        existing_ids = {item.get("id") for item in history}
        added = 0
        for rec in records:
            rec_id = rec.get("id")
            if not rec_id or rec_id in existing_ids:
                continue
            history.append(rec)
            existing_ids.add(rec_id)
            added += 1
        if added:
            _atomic_write(self.history_path, history)
        return added

    @staticmethod
    def make_history_record(
        from_currency: str,
        to_currency: str,
        rate: float,
        source: str,
        timestamp: str | None = None,
        meta: dict | None = None,
    ) -> dict:
        ts = timestamp or _utc_now_iso()
        return {
            "id": f"{from_currency}_{to_currency}_{ts}",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": float(rate),
            "timestamp": ts,
            "source": source,
            "meta": meta or {},
        }

    # ---------- кэш rates.json ----------

    def load_rates(self) -> dict:
        """Прочитать rates.json. Поддерживает и новый ({pairs}), и старый (flat) формат."""
        if not self.rates_path.exists():
            return {"pairs": {}, "last_refresh": None}
        try:
            data = json.loads(self.rates_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"pairs": {}, "last_refresh": None}
        if isinstance(data, dict) and "pairs" in data and isinstance(data["pairs"], dict):
            return data
        # старый flat-формат: {"EUR_USD": {"rate": ...}, ...}
        if isinstance(data, dict):
            pairs = {
                k: v for k, v in data.items()
                if isinstance(v, dict) and "rate" in v
            }
            return {"pairs": pairs, "last_refresh": data.get("last_refresh")}
        return {"pairs": {}, "last_refresh": None}

    def update_rates(self, new_rates: dict[str, float], sources: dict[str, str]) -> dict:
        """Обновить кэш: свежие значения побеждают. Возвращает итоговый dict."""
        cache = self.load_rates()
        pairs = cache.get("pairs", {}) or {}
        now = _utc_now_iso()
        for pair, rate in new_rates.items():
            from_c, _, to_c = pair.partition("_")
            entry = {
                "rate": float(rate),
                "updated_at": now,
                "source": sources.get(pair, "Unknown"),
            }
            existing = pairs.get(pair)
            if existing and isinstance(existing, dict):
                old_ts = existing.get("updated_at") or ""
                if old_ts > now:
                    continue
            pairs[pair] = entry
        result = {"pairs": pairs, "last_refresh": now}
        _atomic_write(self.rates_path, result)
        return result