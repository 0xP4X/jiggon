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
        
        # More lenient AI threshold (Module 4)
        if not mtf_aligned:
            prob *= 0.8  # Less penalizing
            
        if stability == "LOW":
            prob *= 0.9  # Less penalizing
            
        # Recommendation threshold lowered to 40% to allow more trades
        risk = "LOW" if prob >= 0.4 and stability == "HIGH" else "HIGH"
        recommendation = "APPROVED" if prob >= 0.4 else "REJECTED"
        
        return Prediction(prob, stability, risk, recommendation)
