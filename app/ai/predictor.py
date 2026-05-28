from dataclasses import dataclass


@dataclass(frozen=True)
class Prediction:
    trade_probability: float
    market_stability: str
    risk_level: str
    recommendation: str


class RuleBasedPredictor:
    def predict(self, confidence: int, volatility_state: str, mtf_aligned: bool = True) -> Prediction:
        stability = "HIGH" if volatility_state == "normal" else "LOW"
        
        prob = confidence / 100.0
        
        if not mtf_aligned:
            prob *= 0.5
            
        if stability == "LOW":
            prob *= 0.8
            
        risk = "LOW" if prob >= 0.75 and stability == "HIGH" else "HIGH"
        recommendation = "APPROVED" if prob >= 0.75 and risk == "LOW" else "REJECTED"
        
        return Prediction(prob, stability, risk, recommendation)
