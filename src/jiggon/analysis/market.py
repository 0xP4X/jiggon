from collections.abc import Sequence
from dataclasses import dataclass

from jiggon.analysis.indicators import OrderBlock, atr, detect_order_blocks, ema, macd, rsi, vwap


@dataclass(frozen=True)
class MarketSnapshot:
    ema20: float
    ema50: float
    ema200: float
    rsi: float
    atr: float
    macd_line: float
    macd_signal: float
    vwap: float
    order_blocks: list[OrderBlock]
    trend: str
    momentum: str
    volatility_state: str


def classify_trend(ema20: float, ema50: float, ema200: float) -> str:
    if ema20 > ema50 > ema200:
        return "bullish"
    if ema20 < ema50 < ema200:
        return "bearish"
    return "mixed"


def classify_momentum(rsi_value: float, macd_hist: float) -> str:
    if rsi_value > 55 and macd_hist > 0:
        return "bullish"
    if rsi_value < 45 and macd_hist < 0:
        return "bearish"
    return "neutral"


def classify_volatility(atr_value: float, low_threshold: float, high_threshold: float) -> str:
    if atr_value < low_threshold:
        return "dead"
    if atr_value > high_threshold:
        return "unstable"
    return "normal"


def analyze_market(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    atr_low_threshold: float,
    atr_high_threshold: float,
) -> MarketSnapshot:
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200)
    rsi_value = rsi(closes)
    atr_value = atr(highs, lows, closes)
    
    try:
        macd_val, signal_val, hist_val = macd(closes)
    except ValueError:
        macd_val, signal_val, hist_val = 0.0, 0.0, 0.0
        
    vwap_val = vwap(highs, lows, closes, volumes)
    blocks = detect_order_blocks(opens, highs, lows, closes, volumes)

    return MarketSnapshot(
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        rsi=rsi_value,
        atr=atr_value,
        macd_line=macd_val,
        macd_signal=signal_val,
        vwap=vwap_val,
        order_blocks=blocks,
        trend=classify_trend(ema20, ema50, ema200),
        momentum=classify_momentum(rsi_value, hist_val),
        volatility_state=classify_volatility(atr_value, atr_low_threshold, atr_high_threshold),
    )
