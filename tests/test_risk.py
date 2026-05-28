from app.risk.engine import RiskState, evaluate_risk


def test_risk_allows_one_percent_position_size():
    decision = evaluate_risk(
        RiskState(
            account_balance=1_000,
            daily_pnl=0,
            consecutive_losses=0,
            volatility_state="normal",
        )
    )

    assert decision.allowed
    assert decision.stake == 10
    assert not decision.safe_mode_active


def test_risk_activates_safe_mode_after_three_losses():
    decision = evaluate_risk(
        RiskState(
            account_balance=1_000,
            daily_pnl=-20,
            consecutive_losses=3,
            volatility_state="normal",
        )
    )

    assert not decision.allowed
    assert decision.safe_mode_active
    assert "3 consecutive losses" in decision.reason


def test_risk_stops_at_daily_drawdown_limit():
    decision = evaluate_risk(
        RiskState(
            account_balance=1_000,
            daily_pnl=-50,
            consecutive_losses=0,
            volatility_state="normal",
        )
    )

    assert not decision.allowed
    assert decision.safe_mode_active
    assert "daily drawdown limit reached" in decision.reason


def test_risk_reduces_stake_in_cautious_mood():
    decision = evaluate_risk(
        RiskState(
            account_balance=1_000,
            daily_pnl=-10,
            consecutive_losses=1,
            volatility_state="normal",
            mood="cautious",
            stake_multiplier=0.50,
        )
    )

    assert decision.allowed
    assert decision.stake == 5


def test_risk_blocks_locked_mood():
    decision = evaluate_risk(
        RiskState(
            account_balance=1_000,
            daily_pnl=-20,
            consecutive_losses=2,
            volatility_state="normal",
            mood="locked",
            stake_multiplier=0,
        )
    )

    assert not decision.allowed
    assert decision.safe_mode_active
    assert "mood locked" in decision.reason
