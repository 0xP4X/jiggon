from app.risk.mood import MoodInput, evaluate_mood


def test_mood_locks_at_hard_drawdown_limit():
    decision = evaluate_mood(
        MoodInput(
            recent_winrate=0.60,
            drawdown=0.05,
            consecutive_losses=1,
            volatility_state="normal",
            confidence_decay=0,
        )
    )

    assert decision.mood == "locked"
    assert decision.trading_locked
    assert decision.stake_multiplier == 0


def test_mood_turns_defensive_when_multiple_warnings_stack():
    decision = evaluate_mood(
        MoodInput(
            recent_winrate=0.40,
            drawdown=0.035,
            consecutive_losses=3,
            volatility_state="normal",
            confidence_decay=0.20,
        )
    )

    assert decision.mood == "defensive"
    assert decision.stake_multiplier == 0.25


def test_mood_stays_calm_in_stable_conditions():
    decision = evaluate_mood(
        MoodInput(
            recent_winrate=0.64,
            drawdown=0.005,
            consecutive_losses=0,
            volatility_state="normal",
            confidence_decay=0,
        )
    )

    assert decision.mood == "calm"
    assert not decision.trading_locked

