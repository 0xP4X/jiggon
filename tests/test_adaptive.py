from app.strategy.adaptive import AdaptiveContext, dynamic_confidence_threshold


def test_dynamic_threshold_tightens_in_bad_conditions():
    threshold = dynamic_confidence_threshold(
        AdaptiveContext(
            base_threshold=80,
            mood="defensive",
            recent_winrate=0.42,
            session_sample_size=12,
            drawdown=0.035,
            volatility_state="unstable",
        )
    )

    assert threshold == 100


def test_dynamic_threshold_can_relax_slightly_with_large_stable_sample():
    threshold = dynamic_confidence_threshold(
        AdaptiveContext(
            base_threshold=80,
            mood="calm",
            recent_winrate=0.74,
            session_sample_size=80,
            drawdown=0,
            volatility_state="normal",
        )
    )

    assert threshold == 77

