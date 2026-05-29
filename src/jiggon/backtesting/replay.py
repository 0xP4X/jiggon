from dataclasses import dataclass
from datetime import datetime

from jiggon.analysis.market import MarketSnapshot, analyze_market
from jiggon.backtesting.metrics import BacktestMetrics, calculate_metrics
from jiggon.risk.engine import RiskState, evaluate_risk
from jiggon.risk.mood import MoodInput, evaluate_mood
from jiggon.sessions.engine import approve_session
from jiggon.strategy.adaptive import AdaptiveContext
from jiggon.strategy.performance import TradeOutcome, summarize_recent_performance
from jiggon.strategy.rise_fall import TradeSignal
from jiggon.strategy.signals import STRATEGIES, evaluate_strategy


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0


@dataclass(frozen=True)
class BacktestConfig:
    strategy_name: str = "trend_following"
    starting_balance: float = 1_000
    base_confidence_threshold: int = 80
    max_risk_per_trade: float = 0.01
    max_daily_drawdown: float = 0.05
    payout_ratio: float = 0.80
    cost_per_trade: float = 0
    slippage_per_trade: float = 0
    lookback: int = 220
    recent_window: int = 30
    atr_low_threshold: float = 0.05
    atr_high_threshold: float = 10
    session_minimum_winrate: float = 0.55
    session_minimum_sample_size: int = 10
    mean_reversion_oversold: float = 30
    mean_reversion_overbought: float = 70
    channel_period: int = 20


@dataclass(frozen=True)
class TradeRecord:
    timestamp: datetime
    direction: str
    confidence: int
    stake: float
    pnl: float
    balance: float
    mood: str
    reason: list[str]


@dataclass(frozen=True)
class BacktestResult:
    metrics: BacktestMetrics
    starting_balance: float
    ending_balance: float
    peak_balance: float
    trades: list[TradeRecord]
    rejected_signals: int
    rejection_reasons: dict[str, int]


def replay_strategy(
    candles: list[Candle],
    config: BacktestConfig | None = None,
    session_priors: dict[tuple[int, int], tuple[int, int]] | None = None,
) -> BacktestResult:
    config = config or BacktestConfig()
    session_priors = session_priors or {}
    if config.strategy_name not in STRATEGIES:
        raise ValueError(f"unknown strategy: {config.strategy_name}")

    balance = config.starting_balance
    peak_balance = balance
    daily_pnl = 0.0
    current_day = candles[0].timestamp.date() if candles else None
    consecutive_losses = 0
    rejected_signals = 0
    rejection_reasons: dict[str, int] = {}
    trades: list[TradeRecord] = []
    outcomes: list[TradeOutcome] = []

    for index in range(config.lookback, len(candles) - 1):
        candle = candles[index]
        next_candle = candles[index + 1]

        if current_day != candle.timestamp.date():
            current_day = candle.timestamp.date()
            daily_pnl = 0
            consecutive_losses = 0

        window = candles[index - config.lookback : index + 1]
        market = _market_snapshot(window, config)
        recent = summarize_recent_performance(outcomes[-config.recent_window :])
        drawdown = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0
        mood = evaluate_mood(
            MoodInput(
                recent_winrate=recent.winrate if recent.total_trades else 0.60,
                drawdown=drawdown,
                consecutive_losses=consecutive_losses,
                volatility_state=market.volatility_state,
                confidence_decay=recent.confidence_decay,
            )
        )

        session_key = (candle.timestamp.hour, candle.timestamp.weekday())
        prior_wins, prior_total = _session_prior(
            session_priors, session_key, config.session_minimum_sample_size
        )
        live_session = _session_counts(trades, session_key)
        session_total = prior_total + live_session[1]
        session_wins = prior_wins + live_session[0]
        session_winrate = session_wins / session_total if session_total else 0
        session = approve_session(
            hour=session_key[0],
            weekday=session_key[1],
            winrate=session_winrate,
            minimum_winrate=config.session_minimum_winrate,
            sample_size=session_total,
            minimum_sample_size=config.session_minimum_sample_size,
        )

        adaptive = AdaptiveContext(
            base_threshold=config.base_confidence_threshold,
            mood=mood.mood,
            recent_winrate=recent.winrate if recent.total_trades else 0.60,
            session_sample_size=session.sample_size,
            drawdown=drawdown,
            volatility_state=market.volatility_state,
        )
        signal = evaluate_strategy(
            strategy_name=config.strategy_name,
            candles=window,
            market=market,
            session_approved=session.allow_trading,
            candle_strong=_strong_candle(candle),
            safe_mode_active=mood.trading_locked,
            adaptive_context=adaptive,
            mean_reversion_oversold=config.mean_reversion_oversold,
            mean_reversion_overbought=config.mean_reversion_overbought,
            channel_period=config.channel_period,
        )
        risk = evaluate_risk(
            RiskState(
                account_balance=balance,
                daily_pnl=daily_pnl,
                consecutive_losses=consecutive_losses,
                volatility_state=market.volatility_state,
                mood=mood.mood,
                stake_multiplier=mood.stake_multiplier,
            ),
            max_risk_per_trade=config.max_risk_per_trade,
            max_daily_drawdown=config.max_daily_drawdown,
        )

        if not signal.approved or not risk.allowed:
            rejected_signals += 1
            reasons = signal.reason if not signal.approved else risk.reason
            _count_rejections(rejection_reasons, reasons)
            continue

        pnl = _settle_trade(signal, candle.close, next_candle.close, risk.stake, config)
        balance = round(balance + pnl, 2)
        peak_balance = max(peak_balance, balance)
        daily_pnl += pnl
        consecutive_losses = consecutive_losses + 1 if pnl < 0 else 0
        outcomes.append(TradeOutcome(pnl=pnl, confidence=signal.confidence))
        trades.append(
            TradeRecord(
                timestamp=next_candle.timestamp,
                direction=signal.direction,
                confidence=signal.confidence,
                stake=risk.stake,
                pnl=pnl,
                balance=balance,
                mood=mood.mood,
                reason=signal.reason + risk.reason + mood.reasons,
            )
        )

    pnls = [trade.pnl for trade in trades]
    metrics = calculate_metrics(pnls, peak_balance=peak_balance, ending_balance=balance)
    return BacktestResult(
        metrics,
        config.starting_balance,
        balance,
        peak_balance,
        trades,
        rejected_signals,
        rejection_reasons,
    )


def _market_snapshot(candles: list[Candle], config: BacktestConfig) -> MarketSnapshot:
    return analyze_market(
        closes=[candle.close for candle in candles],
        highs=[candle.high for candle in candles],
        lows=[candle.low for candle in candles],
        atr_low_threshold=config.atr_low_threshold,
        atr_high_threshold=config.atr_high_threshold,
    )


def _strong_candle(candle: Candle) -> bool:
    candle_range = max(candle.high - candle.low, 0)
    if candle_range == 0:
        return False
    body = abs(candle.close - candle.open)
    return body / candle_range >= 0.60


def _settle_trade(
    signal: TradeSignal,
    entry_price: float,
    exit_price: float,
    stake: float,
    config: BacktestConfig,
) -> float:
    direction_won = (signal.direction == "CALL" and exit_price > entry_price) or (
        signal.direction == "PUT" and exit_price < entry_price
    )
    gross = stake * config.payout_ratio if direction_won else -stake
    return round(gross - config.cost_per_trade - config.slippage_per_trade, 2)


def _session_counts(trades: list[TradeRecord], session_key: tuple[int, int]) -> tuple[int, int]:
    total = 0
    wins = 0
    for trade in trades:
        if (trade.timestamp.hour, trade.timestamp.weekday()) != session_key:
            continue
        total += 1
        wins += int(trade.pnl > 0)
    return wins, total


def _session_prior(
    session_priors: dict[tuple[int, int], tuple[int, int]],
    session_key: tuple[int, int],
    minimum_sample_size: int,
) -> tuple[int, int]:
    exact = session_priors.get(session_key)
    if exact is not None and exact[1] >= minimum_sample_size:
        return exact
    return session_priors.get((session_key[0], -1), exact or (0, 0))


def _count_rejections(target: dict[str, int], reasons: list[str]) -> None:
    for reason in reasons:
        target[reason] = target.get(reason, 0) + 1
