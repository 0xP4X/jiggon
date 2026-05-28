from datetime import datetime, timedelta

from app.backtesting.replay import BacktestConfig, Candle, replay_strategy


def test_replay_applies_costs_and_generates_metrics():
    candles = _trend_candles(280, step=0.4)
    result = replay_strategy(
        candles,
        BacktestConfig(
            lookback=220,
            cost_per_trade=0.10,
            slippage_per_trade=0.05,
            session_minimum_sample_size=1,
            session_minimum_winrate=0.50,
            atr_low_threshold=0.01,
            atr_high_threshold=5,
        ),
        session_priors={(hour, weekday): (10, 10) for hour in range(24) for weekday in range(7)},
    )

    assert result.metrics.total_trades > 0
    assert result.ending_balance > result.starting_balance
    assert all(trade.pnl < trade.stake for trade in result.trades)
    assert result.metrics.profit_factor == float("inf")


def test_replay_can_return_no_trades_when_session_data_is_untrusted():
    candles = _trend_candles(260, step=0.4)
    result = replay_strategy(candles, BacktestConfig(lookback=220, session_minimum_sample_size=50))

    assert result.metrics.total_trades == 0
    assert result.ending_balance == result.starting_balance


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
                high=close_price + 0.10,
                low=open_price - 0.10,
                close=close_price,
            )
        )
        price = close_price
    return candles

