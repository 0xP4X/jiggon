import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public Yahoo Finance OHLC candles to CSV.")
    parser.add_argument("--symbol", required=True, help="Yahoo symbol, for example BTC-USD or EURUSD=X.")
    parser.add_argument("--interval", default="1h", help="Yahoo interval, for example 1h, 1d, 15m.")
    parser.add_argument("--range", default="2y", help="Yahoo range, for example 60d, 1y, 2y.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    args = parser.parse_args()

    rows = fetch_chart(args.symbol, args.interval, args.range)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} candles to {output}")


def fetch_chart(symbol: str, interval: str, range_value: str) -> list[dict]:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{quote(symbol)}?range={quote(range_value)}&interval={quote(interval)}"
    )
    request = Request(url, headers={"User-Agent": "jiggon-backtest/0.1"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote_data = result["indicators"]["quote"][0]
    rows: list[dict] = []
    for index, timestamp in enumerate(timestamps):
        open_price = _value_at(quote_data, "open", index)
        high = _value_at(quote_data, "high", index)
        low = _value_at(quote_data, "low", index)
        close = _value_at(quote_data, "close", index)
        volume = _value_at(quote_data, "volume", index) or 0
        if None in (open_price, high, low, close):
            continue
        rows.append(
            {
                "timestamp": datetime.fromtimestamp(timestamp, tz=UTC).isoformat(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )
    if not rows:
        raise RuntimeError("Yahoo returned no usable candles")
    return rows


def _value_at(data: dict, key: str, index: int):
    values = data.get(key) or []
    return values[index] if index < len(values) else None


if __name__ == "__main__":
    main()

