from app.analysis.market import MarketSnapshot
from app.strategy.adaptive import AdaptiveContext
from app.strategy.rise_fall import evaluate_rise_fall


def test_strategy_rejects_when_adaptive_threshold_tightens():
    market = MarketSnapshot(
        ema20=105,
        ema50=100,
        ema200=95,
        rsi=62,
        atr=1.2,
        trend="bullish",
        momentum="bullish",
        volatility_state="normal",
    )

    signal = evaluate_rise_fall(
        market=market,
        session_approved=True,
        candle_strong=False,
        safe_mode_active=False,
        adaptive_context=AdaptiveContext(
            base_threshold=80,
            mood="defensive",
            recent_winrate=0.42,
            session_sample_size=10,
            drawdown=0.03,
            volatility_state="normal",
        ),
    )

    assert signal.confidence == 85
    assert not signal.approved
    assert "threshold 100" in signal.reason
