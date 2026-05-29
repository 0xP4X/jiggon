import os
from dataclasses import dataclass

def parse_jiggon_strategy(content: str, snapshot, open_price: float, high_price: float, low_price: float, close_price: float):
    """
    Parses a .jiggon script string and evaluates it against the current MarketSnapshot.
    Returns: 'BUY', 'SELL', or 'NONE'
    
    Example syntax:
    IF RSI > 70 AND MACD < 0 THEN SELL
    IF RSI < 30 AND CLOSE < BB_LOWER THEN BUY
    """
    if not content:
        return "NONE"
        
    safe_dict = {
        "RSI": snapshot.rsi,
        "MACD": snapshot.macd_line,
        "MACD_SIGNAL": snapshot.macd_signal,
        "ATR": snapshot.atr,
        "VWAP": snapshot.vwap,
        "BB_UPPER": snapshot.bb_upper,
        "BB_LOWER": snapshot.bb_lower,
        "STOCH_K": snapshot.stoch_k,
        "STOCH_D": snapshot.stoch_d,
        "OPEN": open_price,
        "HIGH": high_price,
        "LOW": low_price,
        "CLOSE": close_price,
        "EMA_TREND": snapshot.trend,
        "BULLISH": "bullish",
        "BEARISH": "bearish",
        "MIXED": "mixed",
        "MOMENTUM": snapshot.momentum,
        "VOLATILITY": snapshot.volatility_state,
        "DEAD": "dead",
        "UNSTABLE": "unstable",
        "NORMAL": "normal"
    }

    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        if line.startswith('IF ') and ' THEN ' in line:
            condition_part, action_part = line[3:].split(' THEN ')
            
            # Allow lowercase 'and' / 'or' usage even if written in caps
            condition_part = condition_part.replace(' AND ', ' and ').replace(' OR ', ' or ')
            
            try:
                # Evaluate the pythonic boolean string using our safe dictionary
                if eval(condition_part, {"__builtins__": None}, safe_dict):
                    direction = action_part.strip().upper()
                    if direction in ["BUY", "SELL"]:
                        return direction
            except Exception:
                continue
                
    return "NONE"
