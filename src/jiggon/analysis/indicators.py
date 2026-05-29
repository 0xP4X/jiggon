from collections.abc import Sequence
from dataclasses import dataclass


def ema(values: Sequence[float], period: int) -> float:
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        raise ValueError("values cannot be empty")

    multiplier = 2 / (period + 1)
    result = float(values[0])
    for value in values[1:]:
        result = (float(value) - result) * multiplier + result
    return result


def ema_series(values: Sequence[float], period: int) -> list[float]:
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []

    multiplier = 2 / (period + 1)
    result = [float(values[0])]
    for value in values[1:]:
        result.append((float(value) - result[-1]) * multiplier + result[-1])
    return result


def macd(values: Sequence[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> tuple[float, float, float]:
    if len(values) < slow_period + signal_period:
        raise ValueError("not enough values for MACD")
    
    fast_emas = ema_series(values, fast_period)
    slow_emas = ema_series(values, slow_period)
    
    macd_lines = [f - s for f, s in zip(fast_emas, slow_emas)]
    signal_line = ema(macd_lines, signal_period)
    
    current_macd = macd_lines[-1]
    histogram = current_macd - signal_line
    return current_macd, signal_line, histogram


def rsi(values: Sequence[float], period: int = 14) -> float:
    if len(values) <= period:
        raise ValueError("not enough values for RSI")

    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values, values[1:]):
        delta = float(current) - float(previous)
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0

    relative_strength = avg_gain / avg_loss
    return 100 - (100 / (1 + relative_strength))


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float:
    if len(highs) != len(lows) or len(lows) != len(closes):
        raise ValueError("highs, lows, and closes must have the same length")
    if len(closes) <= period:
        raise ValueError("not enough candles for ATR")

    true_ranges: list[float] = []
    for index in range(1, len(closes)):
        high = float(highs[index])
        low = float(lows[index])
        previous_close = float(closes[index - 1])
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))

    return sum(true_ranges[-period:]) / period


def vwap(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], volumes: Sequence[float]) -> float:
    if not (len(highs) == len(lows) == len(closes) == len(volumes)):
        raise ValueError("inputs must have same length")
    if not highs:
        return 0.0
        
    cumulative_tp_vol = 0.0
    cumulative_vol = 0.0
    
    for h, l, c, v in zip(highs, lows, closes, volumes):
        typical_price = (float(h) + float(l) + float(c)) / 3
        cumulative_tp_vol += typical_price * float(v)
        cumulative_vol += float(v)
        
    if cumulative_vol == 0:
        return float(closes[-1])
    return cumulative_tp_vol / cumulative_vol


@dataclass(frozen=True)
class OrderBlock:
    type: str  # "bullish" or "bearish"
    top: float
    bottom: float


def detect_order_blocks(opens: Sequence[float], highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], volumes: Sequence[float], lookback: int = 20) -> list[OrderBlock]:
    blocks = []
    if len(closes) < lookback:
        return blocks
        
    avg_vol = sum(float(v) for v in volumes[-lookback:]) / lookback
    
    for i in range(1, len(closes)):
        prev_close = float(closes[i-1])
        prev_open = float(opens[i-1])
        curr_close = float(closes[i])
        curr_open = float(opens[i])
        curr_vol = float(volumes[i])
        
        # Bullish Engulfing with high volume
        if curr_close > curr_open and prev_close < prev_open and curr_close > prev_open and curr_vol > avg_vol * 1.5:
            blocks.append(OrderBlock("bullish", float(highs[i-1]), float(lows[i-1])))
            
        # Bearish Engulfing with high volume
        if curr_close < curr_open and prev_close > prev_open and curr_close < prev_open and curr_vol > avg_vol * 1.5:
            blocks.append(OrderBlock("bearish", float(highs[i-1]), float(lows[i-1])))
            
    return blocks


def bollinger_bands(closes: Sequence[float], period: int = 20, std_dev_multiplier: float = 2.0) -> tuple[float, float, float]:
    """Returns current (Upper Band, Middle Band, Lower Band)"""
    if len(closes) < period:
        raise ValueError("not enough values for Bollinger Bands")
        
    recent_closes = [float(x) for x in closes[-period:]]
    sma = sum(recent_closes) / period
    
    variance = sum((x - sma) ** 2 for x in recent_closes) / period
    std_dev = variance ** 0.5
    
    upper_band = sma + (std_dev * std_dev_multiplier)
    lower_band = sma - (std_dev * std_dev_multiplier)
    
    return upper_band, sma, lower_band


def stochastic(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], k_period: int = 14, d_period: int = 3) -> tuple[float, float]:
    """Returns current (%K, %D)"""
    if len(highs) < k_period + d_period or len(lows) < k_period + d_period or len(closes) < k_period + d_period:
        raise ValueError("not enough values for Stochastic Oscillator")
        
    # Calculate fast %K for each of the last d_period candles
    fast_k_values = []
    for i in range(d_period):
        idx_end = len(closes) - i
        idx_start = idx_end - k_period
        
        period_highs = [float(x) for x in highs[idx_start:idx_end]]
        period_lows = [float(x) for x in lows[idx_start:idx_end]]
        
        highest_high = max(period_highs)
        lowest_low = min(period_lows)
        current_close = float(closes[idx_end - 1])
        
        if highest_high - lowest_low == 0:
            fast_k = 50.0
        else:
            fast_k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
            
        fast_k_values.insert(0, fast_k)  # insert at beginning to maintain chronological order
        
    current_k = fast_k_values[-1]
    current_d = sum(fast_k_values) / d_period  # Simple moving average of %K
    
    return current_k, current_d

