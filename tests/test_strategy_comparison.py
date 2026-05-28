from app.backtesting.comparison import compare_strategies, write_comparison
from app.backtesting.replay import BacktestConfig
from tests.test_walk_forward import _trend_candles


def test_compare_strategies_returns_all_requested_rows(tmp_path):
    rows = compare_strategies(
        candles=_trend_candles(2_500, step=0.35),
        base_config=BacktestConfig(
            lookback=220,
            session_minimum_sample_size=1,
            session_minimum_winrate=0.50,
            atr_low_threshold=0.01,
            atr_high_threshold=5,
        ),
        train_size=1_500,
        test_size=260,
        step_size=260,
        strategy_names=("trend_following", "channel_breakout"),
        output_dir=tmp_path,
    )

    assert [row.strategy_name for row in rows] == ["trend_following", "channel_breakout"]
    assert rows[0].total_trades > 0

    json_path, markdown_path = write_comparison(rows, tmp_path)
    assert json_path.exists()
    assert markdown_path.exists()

