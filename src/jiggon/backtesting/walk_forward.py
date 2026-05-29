from dataclasses import dataclass

from jiggon.backtesting.metrics import BacktestMetrics, calculate_metrics
from jiggon.backtesting.replay import BacktestConfig, BacktestResult, Candle, replay_strategy


@dataclass(frozen=True)
class WalkForwardFold:
    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    result: BacktestResult


@dataclass(frozen=True)
class WalkForwardReport:
    folds: list[WalkForwardFold]
    aggregate_metrics: BacktestMetrics
    pass_rate: float
    verdict: str
    reasons: list[str]


def run_walk_forward(
    candles: list[Candle],
    train_size: int,
    test_size: int,
    step_size: int,
    config: BacktestConfig | None = None,
    minimum_expectancy: float = 0,
    minimum_profit_factor: float = 1.10,
    maximum_drawdown: float = 0.10,
) -> WalkForwardReport:
    if train_size <= 0 or test_size <= 0 or step_size <= 0:
        raise ValueError("train_size, test_size, and step_size must be positive")
    if len(candles) < train_size + test_size:
        raise ValueError("not enough candles for one walk-forward fold")

    config = config or BacktestConfig()
    folds: list[WalkForwardFold] = []
    all_pnls: list[float] = []
    fold_number = 1
    start = 0

    while start + train_size + test_size <= len(candles):
        train = candles[start : start + train_size]
        test = candles[start + train_size : start + train_size + test_size]
        session_priors = _learn_session_priors(train)
        result = replay_strategy(test, config=config, session_priors=session_priors)
        folds.append(
            WalkForwardFold(
                fold=fold_number,
                train_start=start,
                train_end=start + train_size,
                test_start=start + train_size,
                test_end=start + train_size + test_size,
                result=result,
            )
        )
        all_pnls.extend(trade.pnl for trade in result.trades)
        fold_number += 1
        start += step_size

    peak_balance, ending_balance = _compound_equity(all_pnls, config.starting_balance)
    aggregate = calculate_metrics(all_pnls, peak_balance=peak_balance, ending_balance=ending_balance)
    passing_folds = [
        fold
        for fold in folds
        if _fold_passes(fold.result.metrics, minimum_expectancy, minimum_profit_factor, maximum_drawdown)
    ]
    pass_rate = len(passing_folds) / len(folds) if folds else 0
    reasons = _verdict_reasons(aggregate, pass_rate, minimum_expectancy, minimum_profit_factor, maximum_drawdown)
    verdict = "pass" if not reasons else "fail"

    return WalkForwardReport(folds=folds, aggregate_metrics=aggregate, pass_rate=pass_rate, verdict=verdict, reasons=reasons)


def _compound_equity(pnls: list[float], starting_balance: float) -> tuple[float, float]:
    balance = starting_balance
    peak = starting_balance
    for pnl in pnls:
        balance = round(balance + pnl, 2)
        peak = max(peak, balance)
    return peak, balance


def _learn_session_priors(candles: list[Candle]) -> dict[tuple[int, int], tuple[int, int]]:
    priors: dict[tuple[int, int], list[int]] = {}
    for previous, current in zip(candles, candles[1:]):
        previous_direction = _candle_direction(previous)
        if previous_direction == 0:
            continue
        won = int((current.close - previous.close) * previous_direction > 0)
        for key in ((previous.timestamp.hour, previous.timestamp.weekday()), (previous.timestamp.hour, -1)):
            stats = priors.setdefault(key, [0, 0])
            stats[1] += 1
            stats[0] += won
    return {key: (stats[0], stats[1]) for key, stats in priors.items()}


def _candle_direction(candle: Candle) -> int:
    if candle.close > candle.open:
        return 1
    if candle.close < candle.open:
        return -1
    return 0


def _fold_passes(
    metrics: BacktestMetrics,
    minimum_expectancy: float,
    minimum_profit_factor: float,
    maximum_drawdown: float,
) -> bool:
    return (
        metrics.total_trades > 0
        and metrics.expectancy > minimum_expectancy
        and metrics.profit_factor >= minimum_profit_factor
        and metrics.drawdown <= maximum_drawdown
    )


def _verdict_reasons(
    metrics: BacktestMetrics,
    pass_rate: float,
    minimum_expectancy: float,
    minimum_profit_factor: float,
    maximum_drawdown: float,
) -> list[str]:
    reasons: list[str] = []
    if metrics.total_trades == 0:
        reasons.append("no out-of-sample trades")
    if metrics.expectancy <= minimum_expectancy:
        reasons.append("expectancy below target")
    if metrics.profit_factor < minimum_profit_factor:
        reasons.append("profit factor below target")
    if metrics.drawdown > maximum_drawdown:
        reasons.append("drawdown above limit")
    if pass_rate < 0.60:
        reasons.append("too few folds passed")
    return reasons
