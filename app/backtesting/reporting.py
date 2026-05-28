import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.backtesting.walk_forward import WalkForwardReport


@dataclass(frozen=True)
class ReportSummary:
    verdict: str
    reasons: list[str]
    folds: int
    pass_rate: float
    total_trades: int
    win_rate: float
    expectancy: float
    profit_factor: float
    max_drawdown: float
    max_loss_streak: int


def summarize_walk_forward(report: WalkForwardReport) -> ReportSummary:
    metrics = report.aggregate_metrics
    return ReportSummary(
        verdict=report.verdict,
        reasons=report.reasons,
        folds=len(report.folds),
        pass_rate=report.pass_rate,
        total_trades=metrics.total_trades,
        win_rate=metrics.win_rate,
        expectancy=metrics.expectancy,
        profit_factor=metrics.profit_factor,
        max_drawdown=metrics.drawdown,
        max_loss_streak=metrics.max_loss_streak,
    )


def write_report_files(report: WalkForwardReport, output_dir: str | Path) -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    summary = summarize_walk_forward(report)
    json_path = destination / "walk_forward_report.json"
    markdown_path = destination / "walk_forward_report.md"

    json_path.write_text(json.dumps(_report_payload(report, summary), indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown_report(report, summary), encoding="utf-8")
    return json_path, markdown_path


def _report_payload(report: WalkForwardReport, summary: ReportSummary) -> dict:
    return {
        "summary": asdict(summary),
        "folds": [
            {
                "fold": fold.fold,
                "train_start": fold.train_start,
                "train_end": fold.train_end,
                "test_start": fold.test_start,
                "test_end": fold.test_end,
                "starting_balance": fold.result.starting_balance,
                "ending_balance": fold.result.ending_balance,
                "rejected_signals": fold.result.rejected_signals,
                "rejection_reasons": fold.result.rejection_reasons,
                "metrics": asdict(fold.result.metrics),
            }
            for fold in report.folds
        ],
    }


def _markdown_report(report: WalkForwardReport, summary: ReportSummary) -> str:
    reasons = ", ".join(summary.reasons) if summary.reasons else "none"
    lines = [
        "# Walk-Forward Report",
        "",
        f"- Verdict: {summary.verdict}",
        f"- Reasons: {reasons}",
        f"- Folds: {summary.folds}",
        f"- Pass rate: {summary.pass_rate:.2%}",
        f"- Total trades: {summary.total_trades}",
        f"- Win rate: {summary.win_rate:.2%}",
        f"- Expectancy: {summary.expectancy:.4f}",
        f"- Profit factor: {summary.profit_factor:.4f}",
        f"- Max drawdown: {summary.max_drawdown:.2%}",
        f"- Max loss streak: {summary.max_loss_streak}",
        "",
        "| Fold | Trades | Win Rate | Expectancy | Profit Factor | Drawdown | Rejected | Top Rejection |",
        "|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for fold in report.folds:
        metrics = fold.result.metrics
        lines.append(
            "| "
            f"{fold.fold} | "
            f"{metrics.total_trades} | "
            f"{metrics.win_rate:.2%} | "
            f"{metrics.expectancy:.4f} | "
            f"{metrics.profit_factor:.4f} | "
            f"{metrics.drawdown:.2%} | "
            f"{fold.result.rejected_signals} | "
            f"{_top_rejection(fold.result.rejection_reasons)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _top_rejection(reasons: dict[str, int]) -> str:
    if not reasons:
        return "none"
    reason, count = max(reasons.items(), key=lambda item: item[1])
    return f"{reason} ({count})"
