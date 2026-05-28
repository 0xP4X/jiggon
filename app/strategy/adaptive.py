from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveContext:
    base_threshold: int
    mood: str
    recent_winrate: float
    session_sample_size: int
    drawdown: float
    volatility_state: str


def dynamic_confidence_threshold(context: AdaptiveContext) -> int:
    threshold = context.base_threshold

    if context.session_sample_size < 30:
        threshold += 5
    if context.recent_winrate < 0.50:
        threshold += 10
    elif context.recent_winrate < 0.58:
        threshold += 5
    elif context.recent_winrate >= 0.70 and context.session_sample_size >= 50:
        threshold -= 3

    if context.drawdown >= 0.03:
        threshold += 10
    elif context.drawdown >= 0.015:
        threshold += 5

    if context.volatility_state != "normal":
        threshold += 10

    mood_adjustments = {
        "calm": 0,
        "cautious": 5,
        "defensive": 15,
        "locked": 100,
    }
    threshold += mood_adjustments.get(context.mood, 15)

    return max(60, min(100, threshold))

