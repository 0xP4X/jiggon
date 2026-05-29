import os
from dataclasses import dataclass

def parse_jiggon_strategy(content: str, snapshot):
    """
    Parses a .jiggon script string and evaluates it against the current MarketSnapshot.
    Returns: 'BUY', 'SELL', or 'NONE'
    
    Example syntax:
    IF RSI > 70 AND MACD < 0 THEN SELL
    IF RSI < 30 AND EMA_TREND == BULLISH THEN BUY
    """
    if not content:
        return "NONE"

    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        if line.startswith('IF ') and ' THEN ' in line:
            condition_part, action_part = line[3:].split(' THEN ')
            
            # Replace DSL variables with snapshot values
            condition = condition_part.replace('RSI', str(snapshot.rsi))
            condition = condition.replace('MACD', str(snapshot.macd_line))
            condition = condition.replace('ATR', str(snapshot.atr))
            
            condition = condition.replace('EMA_TREND == BEARISH', 'True' if snapshot.trend == 'bearish' else 'False')
            condition = condition.replace('EMA_TREND == BULLISH', 'True' if snapshot.trend == 'bullish' else 'False')
            condition = condition.replace('EMA_TREND == MIXED', 'True' if snapshot.trend == 'mixed' else 'False')
            
            condition = condition.replace('AND', 'and')
            condition = condition.replace('OR', 'or')
            
            try:
                # Evaluate the pythonic boolean string
                if eval(condition):
                    direction = action_part.strip().upper()
                    if direction in ["BUY", "SELL"]:
                        return direction
            except Exception:
                continue
                
    return "NONE"
