import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backtesting import BacktestConfig, compare_strategies, load_candles_csv, write_comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare strategy families on one walk-forward dataset.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--output-dir", default="reports/strategy_comparison")
    parser.add_argument("--train-size", type=int, default=3_000)
    parser.add_argument("--test-size", type=int, default=720)
    parser.add_argument("--step-size", type=int, default=720)
    parser.add_argument("--lookback", type=int, default=220)
    parser.add_argument("--cost", type=float, default=0.0)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument("--payout-ratio", type=float, default=0.80)
    parser.add_argument("--atr-low", type=float, default=0.05)
    parser.add_argument("--atr-high", type=float, default=10.0)
    parser.add_argument("--session-min-winrate", type=float, default=0.52)
    parser.add_argument("--session-min-sample", type=int, default=20)
    parser.add_argument("--min-profit-factor", type=float, default=1.10)
    parser.add_argument("--max-drawdown", type=float, default=0.10)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv)
    base_config = BacktestConfig(
        payout_ratio=args.payout_ratio,
        cost_per_trade=args.cost,
        slippage_per_trade=args.slippage,
        lookback=args.lookback,
        atr_low_threshold=args.atr_low,
        atr_high_threshold=args.atr_high,
        session_minimum_winrate=args.session_min_winrate,
        session_minimum_sample_size=args.session_min_sample,
    )
    rows = compare_strategies(
        candles=candles,
        base_config=base_config,
        train_size=args.train_size,
        test_size=args.test_size,
        step_size=args.step_size,
        minimum_profit_factor=args.min_profit_factor,
        maximum_drawdown=args.max_drawdown,
        output_dir=args.output_dir,
    )
    json_path, markdown_path = write_comparison(rows, args.output_dir)
    print(f"json={json_path}")
    print(f"markdown={markdown_path}")
    for row in rows:
        print(
            f"{row.strategy_name}: verdict={row.verdict} trades={row.total_trades} "
            f"win_rate={row.win_rate:.2%} expectancy={row.expectancy:.4f} "
            f"profit_factor={row.profit_factor:.4f} drawdown={row.max_drawdown:.2%}"
        )


if __name__ == "__main__":
    main()

