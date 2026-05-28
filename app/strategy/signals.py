from app.analysis.market import MarketSnapshot

def is_candle_strong(open_price: float, close_price: float, atr: float) -> bool:
    """
    Candle Strength Detection (Module 4)
    A candle is strong if its body is larger than 60% of the ATR.
    """
    if atr == 0:
        return False
    body_size = abs(close_price - open_price)
    return body_size >= (atr * 0.6)

def evaluate_best_strategy(
    market: MarketSnapshot, 
    current_open: float, 
    current_close: float, 
    current_high: float, 
    current_low: float
) -> tuple[str, str]:
    """
    Evaluates multiple strategies and mathematically selects the active one.
    Returns: (strategy_name, direction)
    """
    candle_strong = is_candle_strong(current_open, current_close, market.atr)
    
    # 1. VWAP Rejection Strategy
    vwap_dir = "NONE"
    if current_low <= market.vwap <= current_close and market.momentum == "bullish":
        vwap_dir = "CALL"
    elif current_high >= market.vwap >= current_close and market.momentum == "bearish":
        vwap_dir = "PUT"
        
    # 2. V1 Rise/Fall Trend Strategy (Module 11)
    v1_dir = "NONE"
    if market.trend == "bullish" and market.rsi > 55 and market.atr < 80 and candle_strong and market.momentum == "bullish":
        v1_dir = "CALL"
    elif market.trend == "bearish" and market.rsi < 45 and market.atr < 80 and candle_strong and market.momentum == "bearish":
        v1_dir = "PUT"
        
    # Mathematical Selection Edge: VWAP Sniping > Standard Trend Follow
    if vwap_dir != "NONE":
        return "VWAP_REJECTION", vwap_dir
    elif v1_dir != "NONE":
        return "V1_TREND", v1_dir
        
    return "SCANNING...", "NONE"
