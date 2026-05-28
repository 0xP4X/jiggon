from datetime import datetime

from app.backtesting.io import load_candles_csv
from app.backtesting.reporting import summarize_walk_forward, write_report_files
from app.backtesting.replay import BacktestConfig
from app.backtesting.walk_forward import run_walk_forward
from tests.test_walk_forward import _trend_candles


def test_load_candles_csv_sorts_and_parses(tmp_path):
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume",
                "2026-01-01T00:01:00Z,101,102,100,101.5,20",
                "2026-01-01T00:00:00Z,100,101,99,100.5,10",
            ]
        ),
        encoding="utf-8",
    )

    candles = load_candles_csv(csv_path)

    assert candles[0].timestamp == datetime(2026, 1, 1, 0, 0)
    assert candles[1].close == 101.5


def test_write_report_files_creates_json_and_markdown(tmp_path):
    report = run_walk_forward(
        _trend_candles(2_500, step=0.35),
        train_size=1_500,
        test_size=260,
        step_size=260,
        config=BacktestConfig(
            lookback=220,
            session_minimum_sample_size=1,
            session_minimum_winrate=0.50,
            atr_low_threshold=0.01,
            atr_high_threshold=5,
        ),
    )

    json_path, markdown_path = write_report_files(report, tmp_path)
    summary = summarize_walk_forward(report)

    assert json_path.exists()
    assert markdown_path.exists()
    assert summary.total_trades > 0
    assert "Walk-Forward Report" in markdown_path.read_text(encoding="utf-8")

