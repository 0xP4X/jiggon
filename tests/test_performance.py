from app.strategy.performance import TradeOutcome, summarize_recent_performance


def test_performance_tracks_expectancy_and_loss_streak():
    window = summarize_recent_performance(
        [
            TradeOutcome(2, 90),
            TradeOutcome(-1, 88),
            TradeOutcome(-1, 80),
            TradeOutcome(-1, 76),
            TradeOutcome(3, 70),
        ]
    )

    assert window.total_trades == 5
    assert window.winrate == 0.40
    assert window.max_loss_streak == 3
    assert window.expectancy == 0.40
    assert window.confidence_decay > 0

