import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backtesting import BacktestConfig, load_candles_csv, run_parameter_sweep, write_sweep_report
from app.backtesting.sweep import DEFAULT_SWEEP_GRID, QUICK_SWEEP_GRID


def main() -> None:
    parser = argparse.ArgumentParser(description="Run walk-forward parameter sweep with anti-overfit warnings.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--output-dir", default="reports/parameter_sweep")
    parser.add_argument("--train-size", type=int, default=3_000)
    parser.add_argument("--test-size", type=int, default=720)
    parser.add_argument("--step-size", type=int, default=720)
    parser.add_argument("--lookback", type=int, default=220)
    parser.add_argument("--cost", type=float, default=0.0)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument("--payout-ratio", type=float, default=0.80)
    parser.add_argument("--atr-low", type=float, default=0.05)
    parser.add_argument("--atr-high", type=float, default=10.0)
    parser.add_argument("--session-min-sample", type=int, default=20)
    parser.add_argument("--min-profit-factor", type=float, default=1.10)
    parser.add_argument("--max-drawdown", type=float, default=0.10)
    parser.add_argument("--limit", type=int, default=None, help="Limit candidate count for resumable audits.")
    parser.add_argument("--full-grid", action="store_true", help="Use the full 243-candidate grid.")
    parser.add_argument("--quiet", action="store_true", help="Disable progress output.")
    args = parser.parse_args()

    grid = DEFAULT_SWEEP_GRID if args.full_grid else QUICK_SWEEP_GRID
    candles = load_candles_csv(args.csv)
    base_config = BacktestConfig(
        payout_ratio=args.payout_ratio,
        cost_per_trade=args.cost,
        slippage_per_trade=args.slippage,
        lookback=args.lookback,
        atr_low_threshold=args.atr_low,
        atr_high_threshold=args.atr_high,
        session_minimum_sample_size=args.session_min_sample,
    )
    candidates = run_parameter_sweep(
        candles=candles,
        base_config=base_config,
        train_size=args.train_size,
        test_size=args.test_size,
        step_size=args.step_size,
        grid=grid,
        minimum_profit_factor=args.min_profit_factor,
        maximum_drawdown=args.max_drawdown,
        limit=args.limit,
        progress=None if args.quiet else _progress,
    )
    json_path, markdown_path = write_sweep_report(candidates, args.output_dir)
    print(f"json={json_path}")
    print(f"markdown={markdown_path}")
    for candidate in candidates[:10]:
        print(
            f"{candidate.parameters}: verdict={candidate.verdict} trades={candidate.total_trades} "
            f"win_rate={candidate.win_rate:.2%} expectancy={candidate.expectancy:.4f} "
            f"profit_factor={candidate.profit_factor:.4f} drawdown={candidate.max_drawdown:.2%} "
            f"pass_rate={candidate.pass_rate:.2%} warnings={candidate.overfit_warnings}"
        )

def _progress(current: int, total: int, parameters: dict) -> None:
    print(f"[{current}/{total}] {parameters}", flush=True)


if __name__ == "__main__":
    main()
