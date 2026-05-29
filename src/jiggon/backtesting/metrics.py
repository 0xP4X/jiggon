from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestMetrics:
    total_trades: int
    win_rate: float
    average_profit: float
    average_loss: float
    expectancy: float
    drawdown: float
    profit_factor: float
    max_loss_streak: int


def calculate_metrics(pnls: list[float], peak_balance: float, ending_balance: float) -> BacktestMetrics:
    if not pnls:
        return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0)

    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [abs(pnl) for pnl in pnls if pnl < 0]
    win_probability = len(wins) / len(pnls)
    loss_probability = len(losses) / len(pnls)
    average_profit = sum(wins) / len(wins) if wins else 0
    average_loss = sum(losses) / len(losses) if losses else 0
    expectancy = (win_probability * average_profit) - (loss_probability * average_loss)
    drawdown = (peak_balance - ending_balance) / peak_balance if peak_balance > 0 else 0
    profit_factor = sum(wins) / sum(losses) if losses else float("inf")

    max_loss_streak = 0
    current_loss_streak = 0
    for pnl in pnls:
        if pnl < 0:
            current_loss_streak += 1
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_loss_streak = 0

    return BacktestMetrics(
        total_trades=len(pnls),
        win_rate=win_probability,
        average_profit=average_profit,
        average_loss=average_loss,
        expectancy=expectancy,
        drawdown=drawdown,
        profit_factor=profit_factor,
        max_loss_streak=max_loss_streak,
    )
