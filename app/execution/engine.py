from dataclasses import dataclass

from app.risk.engine import RiskDecision
from app.ai.predictor import Prediction

@dataclass(frozen=True)
class TradeSignal:
    approved: bool
    direction: str
    reason: list[str]



@dataclass(frozen=True)
class ExecutionDecision:
    execute: bool
    direction: str
    stake: float
    reason: list[str]


def validate_execution(signal: TradeSignal, risk: RiskDecision, prediction: Prediction | None = None) -> ExecutionDecision:
    if not signal.approved:
        return ExecutionDecision(False, "NONE", 0, signal.reason)
    if not risk.allowed:
        return ExecutionDecision(False, "NONE", 0, risk.reason)
        
    reasons = signal.reason + risk.reason
    
    if prediction is not None:
        if prediction.recommendation != "APPROVED":
            reasons.append(f"AI VETO: probability {prediction.trade_probability:.2%}")
            return ExecutionDecision(False, "NONE", 0, reasons)
        else:
            reasons.append(f"AI APPROVED: probability {prediction.trade_probability:.2%}")
            
    return ExecutionDecision(True, signal.direction, risk.stake, reasons)
