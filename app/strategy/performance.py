from dataclasses import dataclass


@dataclass(frozen=True)
class TradeOutcome:
    pnl: float
    confidence: int


@dataclass(frozen=True)
class PerformanceWindow:
    total_trades: int
    winrate: float
    average_confidence: float
    confidence_decay: float
    max_loss_streak: int
    expectancy: float


def summarize_recent_performance(outcomes: list[TradeOutcome]) -> PerformanceWindow:
    if not outcomes:
        return PerformanceWindow(0, 0, 0, 0, 0, 0)

    wins = [outcome.pnl for outcome in outcomes if outcome.pnl > 0]
    losses = [abs(outcome.pnl) for outcome in outcomes if outcome.pnl < 0]
    winrate = len(wins) / len(outcomes)
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    expectancy = (winrate * avg_win) - ((1 - winrate) * avg_loss)

    midpoint = max(1, len(outcomes) // 2)
    first_half_confidence = sum(item.confidence for item in outcomes[:midpoint]) / midpoint
    second_half = outcomes[midpoint:] or outcomes[-1:]
    second_half_confidence = sum(item.confidence for item in second_half) / len(second_half)
    confidence_decay = max(0, (first_half_confidence - second_half_confidence) / 100)

    max_loss_streak = 0
    current_loss_streak = 0
    for outcome in outcomes:
        if outcome.pnl < 0:
            current_loss_streak += 1
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_loss_streak = 0

    return PerformanceWindow(
        total_trades=len(outcomes),
        winrate=winrate,
        average_confidence=sum(item.confidence for item in outcomes) / len(outcomes),
        confidence_decay=confidence_decay,
        max_loss_streak=max_loss_streak,
        expectancy=expectancy,
    )

