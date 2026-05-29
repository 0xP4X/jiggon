import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jiggon.backtesting import BacktestConfig, load_candles_csv, run_walk_forward, write_report_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a walk-forward strategy report from OHLC CSV.")
    parser.add_argument("--csv", required=True, help="Input OHLC CSV path.")
    parser.add_argument("--strategy", default="trend_following")
    parser.add_argument("--output-dir", default="reports/latest", help="Directory for report files.")
    parser.add_argument("--train-size", type=int, default=1_500)
    parser.add_argument("--test-size", type=int, default=300)
    parser.add_argument("--step-size", type=int, default=300)
    parser.add_argument("--lookback", type=int, default=220)
    parser.add_argument("--cost", type=float, default=0.0)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument("--payout-ratio", type=float, default=0.80)
    parser.add_argument("--starting-balance", type=float, default=1_000)
    parser.add_argument("--atr-low", type=float, default=0.05)
    parser.add_argument("--atr-high", type=float, default=10.0)
    parser.add_argument("--session-min-winrate", type=float, default=0.55)
    parser.add_argument("--session-min-sample", type=int, default=10)
    parser.add_argument("--min-profit-factor", type=float, default=1.10)
    parser.add_argument("--max-drawdown", type=float, default=0.10)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv)
    config = BacktestConfig(
        strategy_name=args.strategy,
        starting_balance=args.starting_balance,
        payout_ratio=args.payout_ratio,
        cost_per_trade=args.cost,
        slippage_per_trade=args.slippage,
        lookback=args.lookback,
        atr_low_threshold=args.atr_low,
        atr_high_threshold=args.atr_high,
        session_minimum_winrate=args.session_min_winrate,
        session_minimum_sample_size=args.session_min_sample,
    )
    report = run_walk_forward(
        candles,
        train_size=args.train_size,
        test_size=args.test_size,
        step_size=args.step_size,
        config=config,
        minimum_profit_factor=args.min_profit_factor,
        maximum_drawdown=args.max_drawdown,
    )
    json_path, markdown_path = write_report_files(report, args.output_dir)
    print(f"verdict={report.verdict}")
    print(f"reasons={report.reasons}")
    print(f"json={json_path}")
    print(f"markdown={markdown_path}")


if __name__ == "__main__":
    main()
