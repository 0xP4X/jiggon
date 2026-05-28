from dataclasses import dataclass


@dataclass(frozen=True)
class MoodInput:
    recent_winrate: float
    drawdown: float
    consecutive_losses: int
    volatility_state: str
    confidence_decay: float


@dataclass(frozen=True)
class MoodDecision:
    mood: str
    threshold_offset: int
    stake_multiplier: float
    trading_locked: bool
    reasons: list[str]


def evaluate_mood(inputs: MoodInput) -> MoodDecision:
    reasons: list[str] = []

    if inputs.consecutive_losses >= 5 or inputs.drawdown >= 0.05:
        reasons.append("hard risk limit reached")
        return MoodDecision("locked", 100, 0, True, reasons)

    if inputs.consecutive_losses >= 3:
        reasons.append("loss streak")
    if inputs.drawdown >= 0.03:
        reasons.append("drawdown pressure")
    if inputs.volatility_state == "unstable":
        reasons.append("unstable volatility")
    if inputs.recent_winrate < 0.45:
        reasons.append("recent winrate degraded")
    if inputs.confidence_decay >= 0.15:
        reasons.append("confidence decay")

    if len(reasons) >= 2:
        return MoodDecision("defensive", 15, 0.25, False, reasons)
    if reasons or inputs.recent_winrate < 0.55 or inputs.volatility_state == "dead":
        if not reasons:
            reasons.append("weak trading mood")
        return MoodDecision("cautious", 5, 0.50, False, reasons)

    return MoodDecision("calm", 0, 1.0, False, ["conditions stable"])

