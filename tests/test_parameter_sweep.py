from app.backtesting.replay import BacktestConfig
from app.backtesting.sweep import QUICK_SWEEP_GRID, run_parameter_sweep, write_sweep_report
from tests.test_walk_forward import _trend_candles


def test_parameter_sweep_ranks_candidates_and_writes_report(tmp_path):
    candidates = run_parameter_sweep(
        candles=_trend_candles(2_500, step=0.35),
        base_config=BacktestConfig(
            lookback=220,
            session_minimum_sample_size=1,
            atr_low_threshold=0.01,
            atr_high_threshold=5,
        ),
        train_size=1_500,
        test_size=260,
        step_size=260,
        grid={
            "strategy_name": ["trend_following", "channel_breakout"],
            "base_confidence_threshold": [75],
            "session_minimum_winrate": [0.50],
            "mean_reversion_oversold": [30],
            "mean_reversion_overbought": [70],
            "channel_period": [20],
        },
    )

    assert len(candidates) == 2
    assert candidates[0].profit_factor >= candidates[1].profit_factor

    json_path, markdown_path = write_sweep_report(candidates, tmp_path)
    assert json_path.exists()
    assert markdown_path.exists()


def test_quick_grid_stays_small_for_interactive_runs():
    total = 1
    for values in QUICK_SWEEP_GRID.values():
        total *= len(values)

    assert total == 12
