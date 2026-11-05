"""RatesUpdater: опрос клиентов, объединение, сохранение в storage."""

from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    build_clients,
)
from valutatrade_hub.parser_service.storage import RatesStorage

logger = get_logger()


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


class RatesUpdater:
    """Точка входа логики парсинга: опрос клиентов → storage."""

    def __init__(
        self,
        clients: list[BaseApiClient] | None = None,
        storage: RatesStorage | None = None,
    ):
        self.clients = clients if clients is not None else build_clients()
        self.storage = storage or RatesStorage()

    def run_update(self) -> dict:
        """Обновить курсы. Возвращает сводку для CLI."""
        logger.info("Starting rates update...")
        merged: dict[str, float] = {}
        sources: dict[str, str] = {}
        errors: list[str] = []

        for client in self.clients:
            try:
                rates = client.fetch_rates()
                for pair, rate in rates.items():
                    merged[pair] = rate
                    sources[pair] = client.name
                logger.info("Fetching from %s... OK (%d rates)", client.name, len(rates))
            except ApiRequestError as exc:
                errors.append(f"{client.name}: {exc.reason if hasattr(exc, 'reason') else exc}")
                logger.error("Failed to fetch from %s: %s", client.name, exc)
            except Exception as exc:  # не роняем весь апдейт из-за одного клиента
                errors.append(f"{client.name}: неожиданная ошибка ({exc})")
                logger.exception("Unexpected error in %s", client.name)

        if merged:
            logger.info("Writing %d rates to %s...", len(merged), self.storage.rates_path)
            result = self.storage.update_rates(merged, sources)

            ts = _utc_now_iso()
            history_records = []
            for pair, rate in merged.items():
                from_c, _, to_c = pair.partition("_")
                history_records.append(
                    self.storage.make_history_record(
                        from_currency=from_c,
                        to_currency=to_c,
                        rate=rate,
                        source=sources.get(pair, "Unknown"),
                        timestamp=ts,
                    )
                )
            added = self.storage.append_history(history_records)
            logger.info("History: %d new records", added)

            summary = {
                "updated": len(merged),
                "last_refresh": result.get("last_refresh"),
                "sources": sources,
                "errors": errors,
            }
            if errors:
                logger.warning("Update completed with errors: %s", errors)
            else:
                logger.info("Update successful. Total rates: %d", len(merged))
            return summary

        logger.error("Update failed: no rates received. Errors: %s", errors)
        if errors:
            raise ApiRequestError("; ".join(errors))
        return {
            "updated": 0,
            "last_refresh": None,
            "sources": {},
            "errors": errors,
        }