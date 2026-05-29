import json
from dataclasses import asdict, dataclass
from pathlib import Path

from jiggon.backtesting.reporting import summarize_walk_forward, write_report_files
from jiggon.backtesting.replay import BacktestConfig, Candle
from jiggon.backtesting.walk_forward import run_walk_forward
from jiggon.strategy.signals import STRATEGIES


@dataclass(frozen=True)
class StrategyComparisonRow:
    strategy_name: str
    verdict: str
    pass_rate: float
    total_trades: int
    win_rate: float
    expectancy: float
    profit_factor: float
    max_drawdown: float
    max_loss_streak: int
    reasons: list[str]


def compare_strategies(
    candles: list[Candle],
    base_config: BacktestConfig,
    train_size: int,
    test_size: int,
    step_size: int,
    strategy_names: tuple[str, ...] = STRATEGIES,
    minimum_profit_factor: float = 1.10,
    maximum_drawdown: float = 0.10,
    output_dir: str | Path | None = None,
) -> list[StrategyComparisonRow]:
    rows: list[StrategyComparisonRow] = []
    for strategy_name in strategy_names:
        config = BacktestConfig(**{**base_config.__dict__, "strategy_name": strategy_name})
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
        rows.append(
            StrategyComparisonRow(
                strategy_name=strategy_name,
                verdict=summary.verdict,
                pass_rate=summary.pass_rate,
                total_trades=summary.total_trades,
                win_rate=summary.win_rate,
                expectancy=summary.expectancy,
                profit_factor=summary.profit_factor,
                max_drawdown=summary.max_drawdown,
                max_loss_streak=summary.max_loss_streak,
                reasons=summary.reasons,
            )
        )
        if output_dir is not None:
            write_report_files(report, Path(output_dir) / strategy_name)
    return rows


def write_comparison(rows: list[StrategyComparisonRow], output_dir: str | Path) -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "strategy_comparison.json"
    markdown_path = destination / "strategy_comparison.md"
    json_path.write_text(json.dumps([asdict(row) for row in rows], indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown_comparison(rows), encoding="utf-8")
    return json_path, markdown_path


def _markdown_comparison(rows: list[StrategyComparisonRow]) -> str:
    ordered = sorted(rows, key=_score_row, reverse=True)
    lines = [
        "# Strategy Comparison",
        "",
        "| Strategy | Verdict | Trades | Win Rate | Expectancy | Profit Factor | Drawdown | Pass Rate |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ordered:
        lines.append(
            "| "
            f"{row.strategy_name} | "
            f"{row.verdict} | "
            f"{row.total_trades} | "
            f"{row.win_rate:.2%} | "
            f"{row.expectancy:.4f} | "
            f"{row.profit_factor:.4f} | "
            f"{row.max_drawdown:.2%} | "
            f"{row.pass_rate:.2%} |"
        )
    lines.append("")
    return "\n".join(lines)


def _score_row(row: StrategyComparisonRow) -> tuple[float, float, float, float]:
    return (float(row.verdict == "pass"), row.profit_factor, row.expectancy, -row.max_drawdown)

