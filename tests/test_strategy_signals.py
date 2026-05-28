from app.analysis.market import MarketSnapshot
from app.backtesting.replay import Candle
from app.strategy.adaptive import AdaptiveContext
from app.strategy.signals import STRATEGIES, evaluate_strategy


def test_strategy_registry_contains_research_families():
    assert STRATEGIES == ("trend_following", "mean_reversion", "channel_breakout")


def test_mean_reversion_generates_oversold_call():
    signal = evaluate_strategy(
        strategy_name="mean_reversion",
        candles=[],
        market=MarketSnapshot(ema20=100, ema50=100, ema200=100, rsi=25, atr=1, trend="mixed", momentum="bearish", volatility_state="normal"),
        session_approved=True,
        candle_strong=False,
        safe_mode_active=False,
        adaptive_context=_context(),
    )

    assert signal.direction == "CALL"
    assert signal.approved


def test_channel_breakout_generates_call_on_high_break():
    candles = [Candle(_timestamp(), 100, 101, 99, 100) for _ in range(20)]
    candles.append(Candle(_timestamp(), 101, 103, 100, 102))

    signal = evaluate_strategy(
        strategy_name="channel_breakout",
        candles=candles,
        market=MarketSnapshot(ema20=102, ema50=101, ema200=100, rsi=65, atr=1, trend="bullish", momentum="bullish", volatility_state="normal"),
        session_approved=True,
        candle_strong=True,
        safe_mode_active=False,
        adaptive_context=_context(),
    )

    assert signal.direction == "CALL"
    assert signal.approved


def _context() -> AdaptiveContext:
    return AdaptiveContext(
        base_threshold=80,
        mood="calm",
        recent_winrate=0.65,
        session_sample_size=50,
        drawdown=0,
        volatility_state="normal",
    )


def _timestamp():
    from datetime import datetime

    return datetime(2026, 1, 1)

