from dataclasses import dataclass

@dataclass
class ConfidenceScore:
    total: int
    ema_aligned: bool
    rsi_confirmed: bool
    atr_valid: bool
    session_profitable: bool
    candle_strong: bool
    momentum_valid: bool

def calculate_confidence(
    ema_aligned: bool,
    rsi_confirmed: bool,
    atr_valid: bool,
    session_profitable: bool,
    candle_strong: bool,
    momentum_valid: bool
) -> ConfidenceScore:
    """
    Implements the exact Confidence Scoring System from the Master Spec (Module 6)
    """
    score = 0
    
    if ema_aligned:
        score += 20
    if rsi_confirmed:
        score += 15
    if atr_valid:
        score += 15
    if session_profitable:
        score += 20
    if candle_strong:
        score += 15
    if momentum_valid:
        score += 15
        
    return ConfidenceScore(
        total=score,
        ema_aligned=ema_aligned,
        rsi_confirmed=rsi_confirmed,
        atr_valid=atr_valid,
        session_profitable=session_profitable,
        candle_strong=candle_strong,
        momentum_valid=momentum_valid
    )

def is_trade_approved(score: ConfidenceScore) -> bool:
    """
    Trade Approval Rule from Master Spec
    """
    return score.total >= 80
