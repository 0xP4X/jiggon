import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from app.backtesting.reporting import summarize_walk_forward
from app.backtesting.replay import BacktestConfig, Candle
from app.backtesting.walk_forward import run_walk_forward


@dataclass(frozen=True)
class SweepCandidate:
    name: str
    parameters: dict[str, Any]
    verdict: str
    pass_rate: float
    total_trades: int
    win_rate: float
    expectancy: float
    profit_factor: float
    max_drawdown: float
    max_loss_streak: int
    overfit_warnings: list[str]


DEFAULT_SWEEP_GRID: dict[str, list[Any]] = {
    "strategy_name": ["trend_following", "mean_reversion", "channel_breakout"],
    "base_confidence_threshold": [75, 80, 85],
    "session_minimum_winrate": [0.50, 0.52, 0.55],
    "mean_reversion_oversold": [25, 30, 35],
    "mean_reversion_overbought": [65, 70, 75],
    "channel_period": [10, 20, 40],
}

QUICK_SWEEP_GRID: dict[str, list[Any]] = {
    "strategy_name": ["trend_following", "mean_reversion", "channel_breakout"],
    "base_confidence_threshold": [75, 80],
    "session_minimum_winrate": [0.50, 0.52],
    "mean_reversion_oversold": [30],
    "mean_reversion_overbought": [70],
    "channel_period": [20],
}


class ProgressCallback(Protocol):
    def __call__(self, current: int, total: int, parameters: dict[str, Any]) -> None:
        pass


def run_parameter_sweep(
    candles: list[Candle],
    base_config: BacktestConfig,
    train_size: int,
    test_size: int,
    step_size: int,
    grid: dict[str, list[Any]] | None = None,
    minimum_profit_factor: float = 1.10,
    maximum_drawdown: float = 0.10,
    min_trades: int = 30,
    limit: int | None = None,
    progress: ProgressCallback | None = None,
) -> list[SweepCandidate]:
    grid = grid or DEFAULT_SWEEP_GRID
    candidates: list[SweepCandidate] = []
    candidate_parameters = _candidate_parameters(grid)
    if limit is not None:
        candidate_parameters = candidate_parameters[:limit]
    total = len(candidate_parameters)
    for index, parameters in enumerate(candidate_parameters, start=1):
        if progress is not None:
            progress(index, total, parameters)
        config = BacktestConfig(**{**base_config.__dict__, **parameters})
        report = run_walk_forward(
            candles,
            train_size=train_size,
            test_size=test_size,
            step_size=step_size,
            config=config,
            minimum_profit_factor=minimum_profit_factor,
            maximum_drawdown=maximum_drawdown,
        )
        summary = summarize_walk_forward(report)
        candidates.append(
            SweepCandidate(
                name=_candidate_name(parameters),
                parameters=parameters,
                verdict=summary.verdict,
                pass_rate=summary.pass_rate,
                total_trades=summary.total_trades,
                win_rate=summary.win_rate,
                expectancy=summary.expectancy,
                profit_factor=summary.profit_factor,
                max_drawdown=summary.max_drawdown,
                max_loss_streak=summary.max_loss_streak,
                overfit_warnings=_overfit_warnings(
                    total_trades=summary.total_trades,
                    pass_rate=summary.pass_rate,
                    profit_factor=summary.profit_factor,
                    max_drawdown=summary.max_drawdown,
                    min_trades=min_trades,
                ),
            )
        )
    return sorted(candidates, key=_candidate_score, reverse=True)


def write_sweep_report(candidates: list[SweepCandidate], output_dir: str | Path) -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "parameter_sweep.json"
    markdown_path = destination / "parameter_sweep.md"
    json_path.write_text(json.dumps([asdict(candidate) for candidate in candidates], indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown(candidates), encoding="utf-8")
    return json_path, markdown_path


def _candidate_parameters(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(grid)
    return [dict(zip(keys, values)) for values in itertools.product(*(grid[key] for key in keys))]


def _candidate_name(parameters: dict[str, Any]) -> str:
    return ",".join(f"{key}={value}" for key, value in parameters.items())


def _candidate_score(candidate: SweepCandidate) -> tuple[float, float, float, float, float]:
    warning_penalty = -len(candidate.overfit_warnings)
    return (
        float(candidate.verdict == "pass"),
        candidate.pass_rate,
        candidate.profit_factor,
        candidate.expectancy,
        warning_penalty,
    )


def _overfit_warnings(
    total_trades: int,
    pass_rate: float,
    profit_factor: float,
    max_drawdown: float,
    min_trades: int,
) -> list[str]:
    warnings: list[str] = []
    if total_trades < min_trades:
        warnings.append("too few trades")
    if pass_rate < 0.60:
        warnings.append("weak fold consistency")
    if profit_factor > 2.0 and total_trades < min_trades * 2:
        warnings.append("high profit factor with low sample")
    if max_drawdown > 0.10:
        warnings.append("drawdown too high")
    return warnings


def _markdown(candidates: list[SweepCandidate]) -> str:
    lines = [
        "# Parameter Sweep",
        "",
        "| Rank | Strategy | Verdict | Trades | Win Rate | Expectancy | Profit Factor | Drawdown | Pass Rate | Warnings |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for index, candidate in enumerate(candidates[:25], start=1):
        warnings = ", ".join(candidate.overfit_warnings) if candidate.overfit_warnings else "none"
        lines.append(
            "| "
            f"{index} | "
            f"{candidate.parameters.get('strategy_name')} | "
            f"{candidate.verdict} | "
            f"{candidate.total_trades} | "
            f"{candidate.win_rate:.2%} | "
            f"{candidate.expectancy:.4f} | "
            f"{candidate.profit_factor:.4f} | "
            f"{candidate.max_drawdown:.2%} | "
            f"{candidate.pass_rate:.2%} | "
            f"{warnings} |"
        )
    lines.append("")
    return "\n".join(lines)
