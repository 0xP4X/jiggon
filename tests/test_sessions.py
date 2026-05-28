from app.sessions.engine import approve_session


def test_session_approves_profitable_window():
    decision = approve_session(hour=1, weekday=2, winrate=0.73, sample_size=50)

    assert decision.allow_trading
    assert decision.confidence_multiplier == 15


def test_session_blocks_weak_window():
    decision = approve_session(hour=8, weekday=2, winrate=0.41, sample_size=50)

    assert not decision.allow_trading
    assert decision.confidence_multiplier == -20


def test_session_blocks_tiny_sample_even_with_high_winrate():
    decision = approve_session(hour=1, weekday=2, winrate=0.90, sample_size=8)

    assert not decision.allow_trading
    assert decision.confidence_multiplier == -20
