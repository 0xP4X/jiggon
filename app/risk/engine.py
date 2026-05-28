from dataclasses import dataclass

@dataclass
class RiskState:
    daily_drawdown_pct: float
    daily_profit: float
    consecutive_losses: int
    safe_mode_active: bool
    safe_mode_reason: str

@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    stake: float
    reason: list[str]


def evaluate_risk(
    state: RiskState,
    current_atr: float,
    abnormal_atr_threshold: float,
    max_daily_drawdown: float = 5.0,
    target_profit: float = 0.0,
    max_consecutive_losses: int = 3
) -> RiskState:
    """
    Implements Module 7 (Risk Management) and Module 8 (Safe Mode)
    """
    is_safe = state.safe_mode_active
    reason = state.safe_mode_reason

    # Module 8: Consecutive Loss Protection
    if state.consecutive_losses >= max_consecutive_losses and not is_safe:
        is_safe = True
        reason = f"{max_consecutive_losses} consecutive losses"

    # Module 7: Daily Shutdown Logic (Drawdown)
    if state.daily_drawdown_pct >= max_daily_drawdown and not is_safe:
        is_safe = True
        reason = f"Daily drawdown >= {max_daily_drawdown}%"

    # Take Profit Logic
    if target_profit > 0 and state.daily_profit >= target_profit and not is_safe:
        is_safe = True
        reason = f"Take Profit Reached (${target_profit})"

    # Module 7: Volatility Protection
    if current_atr > abnormal_atr_threshold and not is_safe:
        is_safe = True
        reason = "Abnormal Volatility (High ATR)"

    # If ATR normalizes and there are no other blocks, we could theoretically un-pause,
    # but usually safe mode requires manual or session reset.
    # For now, if ATR was the ONLY reason and it drops, we release it.
    if is_safe and reason == "Abnormal Volatility (High ATR)" and current_atr <= abnormal_atr_threshold:
        is_safe = False
        reason = ""

    return RiskState(
        daily_drawdown_pct=state.daily_drawdown_pct,
        consecutive_losses=state.consecutive_losses,
        safe_mode_active=is_safe,
        safe_mode_reason=reason
    )
