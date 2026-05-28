# Strategy Audit

## Current Flaws Found

- Fixed thresholds can look strong in one market regime and fail in another.
- Win rate alone is not enough. A high win rate can still lose money if average loss is larger than average win.
- The first scaffold had no memory of recent outcomes, so it could not detect confidence decay.
- Safe mode was binary and manual. It did not model cooldown, caution, recovery, or market mood.
- Session approval used a raw win rate without sample-size confidence, so a small number of lucky trades could approve a weak session.
- Backtesting metrics did not include profit factor, loss streak, or quality gates.
- There was no challenge harness to test the bot against random, hostile, choppy, and high-volatility conditions.

## Fix Direction

- Use adaptive thresholds that rise during bad mood, drawdown, weak recent results, and unstable volatility.
- Use mood management states: `calm`, `cautious`, `defensive`, and `locked`.
- Reduce stake size before shutdown instead of using one all-or-nothing rule.
- Require enough samples before trusting a session win rate.
- Evaluate expectancy, profit factor, max loss streak, and drawdown, not just win rate.
- Paper trade and backtest with costs/slippage before enabling live execution.

## Success Rate Rule

The bot must not claim a high success rate until it has out-of-sample evidence. The target is not "more trades"; the target is positive expectancy with controlled drawdown across multiple regimes.

