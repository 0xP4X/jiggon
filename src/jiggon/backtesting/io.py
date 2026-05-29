import csv
from datetime import UTC, datetime
from pathlib import Path

from jiggon.backtesting.replay import Candle


def load_candles_csv(path: str | Path) -> list[Candle]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        candles = [_row_to_candle(_normalize_row(row)) for row in reader]

    candles.sort(key=lambda candle: candle.timestamp)
    _validate_candles(candles)
    return candles


def _normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {key.strip().lower(): value.strip() for key, value in row.items() if key is not None}


def _row_to_candle(row: dict[str, str]) -> Candle:
    timestamp_value = _first(row, "timestamp", "datetime", "date", "time")
    return Candle(
        timestamp=_parse_timestamp(timestamp_value),
        open=float(_first(row, "open", "o")),
        high=float(_first(row, "high", "h")),
        low=float(_first(row, "low", "l")),
        close=float(_first(row, "close", "c", "adj close", "adj_close")),
        volume=float(row.get("volume") or row.get("v") or 0),
    )


def _first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    raise ValueError(f"missing required CSV column, expected one of: {', '.join(keys)}")


def _parse_timestamp(value: str) -> datetime:
    if value.isdigit():
        timestamp = int(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp // 1000
        return datetime.fromtimestamp(timestamp, tz=UTC).replace(tzinfo=None)

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _validate_candles(candles: list[Candle]) -> None:
    if not candles:
        raise ValueError("CSV did not contain any candles")

    previous_timestamp: datetime | None = None
    for candle in candles:
        if candle.high < max(candle.open, candle.close):
            raise ValueError(f"invalid candle high at {candle.timestamp}")
        if candle.low > min(candle.open, candle.close):
            raise ValueError(f"invalid candle low at {candle.timestamp}")
        if previous_timestamp is not None and candle.timestamp == previous_timestamp:
            raise ValueError(f"duplicate candle timestamp: {candle.timestamp}")
        previous_timestamp = candle.timestamp

