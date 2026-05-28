from datetime import datetime, timedelta

from app.backtesting.replay import BacktestConfig, Candle
from app.backtesting.walk_forward import run_walk_forward


def test_walk_forward_passes_consistent_trending_market():
    report = run_walk_forward(
        candles=_trend_candles(2_500, step=0.35),
        train_size=1_500,
        test_size=260,
        step_size=260,
        config=BacktestConfig(
            lookback=220,
            cost_per_trade=0.05,
            slippage_per_trade=0.05,
            session_minimum_sample_size=1,
            session_minimum_winrate=0.50,
            atr_low_threshold=0.01,
            atr_high_threshold=5,
        ),
    )

    assert report.folds
    assert report.verdict == "pass"
    assert report.pass_rate >= 0.60
    assert report.aggregate_metrics.expectancy > 0


def test_walk_forward_fails_when_quality_gates_are_not_met():
    report = run_walk_forward(
        candles=_choppy_candles(2_500),
        train_size=1_500,
        test_size=260,
        step_size=260,
        config=BacktestConfig(
            lookback=220,
            cost_per_trade=0.25,
            slippage_per_trade=0.25,
            session_minimum_sample_size=1,
            session_minimum_winrate=0.50,
            atr_low_threshold=0.01,
            atr_high_threshold=5,
        ),
    )

    assert report.verdict == "fail"
    assert report.reasons


def _trend_candles(count: int, step: float) -> list[Candle]:
    start = datetime(2026, 1, 1)
    candles: list[Candle] = []
    price = 100.0
    for index in range(count):
        open_price = price
        close_price = price + step
        candles.append(
            Candle(
                timestamp=start + timedelta(minutes=index),
                open=open_price,
                high=close_price + 0.08,
                low=open_price - 0.08,
                close=close_price,
            )
        )
        price = close_price
    return candles


def _choppy_candles(count: int) -> list[Candle]:
    start = datetime(2026, 1, 1)
    candles: list[Candle] = []
    price = 100.0
    for index in range(count):
        step = 0.35 if index % 2 == 0 else -0.35
        open_price = price
        close_price = price + step
        candles.append(
            Candle(
                timestamp=start + timedelta(minutes=index),
                open=open_price,
                high=max(open_price, close_price) + 0.08,
                low=min(open_price, close_price) - 0.08,
                close=close_price,
            )
        )
        price = close_price
    return candles
